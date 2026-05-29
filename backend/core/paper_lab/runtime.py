from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

import pandas as pd

from core.paper_lab.daily_window import KST, kst_daily_window
from core.paper_lab.engine import PaperLabEngine
from core.paper_lab.selector import MarketCandidate, select_top_markets


DEFAULT_RUN_ID = "paper_lab_market_scan_v1"
DEFAULT_SELECTION_LIMIT = 10
# Liquidity floor = "major" universe. 5e8 let 161 thin alts through (-49% bleed);
# raised to 1e10 (~25 most-liquid KRW names) to focus on majors — research showed
# the broad pool dilutes the 4h edge (top12 broke out-of-sample, top6-8 held).
DEFAULT_MIN_QUOTE_VOLUME = 10_000_000_000.0
DEFAULT_INTRADAY_REBALANCE_MIN_MINUTES = 180
DEFAULT_INTRADAY_SCORE_IMPROVEMENT = 0.50
# Risk controls (conservative defaults). stop_loss: per-symbol; daily_loss_limit: whole window.
DEFAULT_STOP_LOSS_PCT = 0.05
DEFAULT_DAILY_LOSS_LIMIT_PCT = 0.05
# Phase 2: trailing take-profit — exit when price falls this far from the peak
# since entry (matches trend_rider_4h_v1's native 5% trailing exit).
DEFAULT_TRAILING_STOP_PCT = 0.05
# Universe + confirmation (Phase 1). Backtest showed the universe is the #1 lever:
# same strategy = +16.87% on majors vs -49.35% on the top-24h-gainer alt set.
DEFAULT_SHORTLIST_LIMIT = 30          # how many candidates to confirm before picking
DEFAULT_MAX_PERCENTAGE = 25.0         # overheating cap: skip already-pumped names
# 4h trend-following is the validated edge (15m all lost in research; 4h
# momentum_aggressive / trend_rider held across subsets, OOS, and walk-forward).
DEFAULT_CONFIRM_TIMEFRAME = "4h"
DEFAULT_CONFIRM_HISTORY_LIMIT = 300   # 4h candles per candidate (>=201 needed for signal)
# Regime filter: only open NEW positions when the market leader trends up.
# Overfitting check showed the 4h edge is bull-regime dependent (2022 bear
# -19~-56%); this gate roughly halved bear losses in backtest.
DEFAULT_REGIME_ENABLED = True
DEFAULT_REGIME_SYMBOL = "BTC/KRW"
DEFAULT_REGIME_TIMEFRAME = "4h"
DEFAULT_REGIME_EMA_PERIOD = 200
DEFAULT_REGIME_HISTORY_LIMIT = 300
# Reserved bucket holding undeployed capital when fewer than selection_limit
# confirmed setups exist (lets the lab hold cash instead of forcing full invest).
CASH_BUCKET = "__CASH__"


class MarketDataProvider(Protocol):
    async def get_market_snapshot(self) -> list[MarketCandidate]:
        ...


class PaperLabStore(Protocol):
    def load_state(self, run_id: str) -> dict | None:
        ...

    def save_state(self, run_id: str, state: dict) -> None:
        ...

    def save_snapshot(self, run_id: str, snapshot: dict) -> None:
        ...


@dataclass
class PaperLabConfig:
    total_capital: float = 1_000_000.0
    run_id: str = DEFAULT_RUN_ID
    selection_limit: int = DEFAULT_SELECTION_LIMIT
    min_quote_volume: float = DEFAULT_MIN_QUOTE_VOLUME
    intraday_rebalance_min_minutes: int = DEFAULT_INTRADAY_REBALANCE_MIN_MINUTES
    intraday_score_improvement: float = DEFAULT_INTRADAY_SCORE_IMPROVEMENT
    stop_loss_pct: float = DEFAULT_STOP_LOSS_PCT
    daily_loss_limit_pct: float = DEFAULT_DAILY_LOSS_LIMIT_PCT
    trailing_stop_pct: float = DEFAULT_TRAILING_STOP_PCT
    shortlist_limit: int = DEFAULT_SHORTLIST_LIMIT
    max_percentage: float | None = DEFAULT_MAX_PERCENTAGE
    confirm_timeframe: str = DEFAULT_CONFIRM_TIMEFRAME
    confirm_history_limit: int = DEFAULT_CONFIRM_HISTORY_LIMIT
    regime_enabled: bool = DEFAULT_REGIME_ENABLED
    regime_symbol: str = DEFAULT_REGIME_SYMBOL
    regime_timeframe: str = DEFAULT_REGIME_TIMEFRAME
    regime_ema_period: int = DEFAULT_REGIME_EMA_PERIOD
    regime_history_limit: int = DEFAULT_REGIME_HISTORY_LIMIT


class PaperLabRuntime:
    def __init__(
        self,
        config: PaperLabConfig,
        price_provider: MarketDataProvider,
        store: PaperLabStore,
        now_fn: Callable[[], datetime] | None = None,
        confirmer=None,
    ) -> None:
        self.config = config
        self.price_provider = price_provider
        self.store = store
        self.now_fn = now_fn or (lambda: datetime.now(tz=KST))
        # When set, candidates must pass confirmer.confirm(symbol, ohlcv_df) before
        # being bought. When None, behaviour is unchanged (legacy full-invest path).
        self.confirmer = confirmer

    async def tick(self) -> dict:
        now = self.now_fn()
        window_start, window_end = kst_daily_window(now)
        window_start_iso = window_start.isoformat()
        market_snapshot = await self.price_provider.get_market_snapshot()
        # Shortlist a wider set (with liquidity + overheating filters) so the
        # confirmation gate has candidates to choose from; without a confirmer,
        # the shortlist equals the final selection (legacy behaviour).
        shortlist_limit = (
            self.config.shortlist_limit if self.confirmer is not None
            else self.config.selection_limit
        )
        selected = select_top_markets(
            market_snapshot,
            limit=shortlist_limit,
            min_quote_volume=self.config.min_quote_volume,
            max_percentage=self.config.max_percentage,
        )
        prices = {candidate.symbol: candidate.price for candidate in selected}
        # Confirmed buy-list: only candidates passing the entry signal (capped at
        # selection_limit). May be fewer than selection_limit -> remainder stays cash.
        confirmed_symbols = await self._confirm_symbols([c.symbol for c in selected])
        selected_symbols = confirmed_symbols
        state_doc = self.store.load_state(self.config.run_id)

        if state_doc is None:
            engine = self._build_confirmed_engine(
                selected_symbols, self.config.total_capital, prices, self.config.selection_limit
            )
            event = "initialized"
            rebalance_reason = "initial_selection"
            rebalance_history = [
                _rebalance_event(
                    "initialized",
                    "initial_selection",
                    now,
                    selected_symbols,
                    selected,
                )
            ]
            last_rebalanced_at = now.astimezone(KST).isoformat()
            window_start_equity = self.config.total_capital
            window_realized_pnl = 0.0
            halted = False
        else:
            engine = PaperLabEngine.from_dict(state_doc["engine"])
            previous_window_start = state_doc["window_start"]
            # Exclude the reserved cash bucket from tradable symbol handling.
            held_symbols = [s for s in engine.state.buckets.keys() if s != CASH_BUCKET]
            held_prices = _prices_for_symbols(market_snapshot, held_symbols)
            rebalance_reason = state_doc.get("rebalance_reason", "hold")
            rebalance_history = state_doc.get("rebalance_history", [])
            last_rebalanced_at = state_doc.get("last_rebalanced_at") or state_doc.get("updated_at")
            # Carried-over per-window risk state (legacy states may lack these keys).
            window_start_equity = state_doc.get("window_start_equity")
            window_realized_pnl = state_doc.get("window_realized_pnl", 0.0)
            halted = state_doc.get("halted", False)
            if previous_window_start != window_start_iso:
                previous_summary = engine.summary(held_prices)
                # Surface the full window's realized PnL (intraday rebuilds discard the
                # engine ledger, so accumulate it in window_realized_pnl instead of 0).
                previous_summary["realized_pnl"] = (
                    window_realized_pnl + previous_summary["realized_pnl"]
                )
                self.store.save_snapshot(
                    self.config.run_id,
                    {
                        "window_start": previous_window_start,
                        "window_end": window_start_iso,
                        "summary": previous_summary,
                        "prices": held_prices,
                        "positions": _visible_positions(engine.position_details(held_prices)),
                        "candidate_symbols": [candidate.symbol for candidate in selected],
                        "created_at": now.astimezone(KST).isoformat(),
                    },
                )
                engine = self._build_confirmed_engine(
                    selected_symbols, previous_summary["total_equity"], prices,
                    self.config.selection_limit,
                )
                event = "daily_rebalanced"
                rebalance_reason = "daily_window_rotation"
                last_rebalanced_at = now.astimezone(KST).isoformat()
                rebalance_history = _append_rebalance_history(
                    rebalance_history,
                    _rebalance_event(event, rebalance_reason, now, selected_symbols, selected),
                )
                # New window: reset risk state.
                window_start_equity = previous_summary["total_equity"]
                window_realized_pnl = 0.0
                halted = False
            else:
                if window_start_equity is None:
                    window_start_equity = engine.summary(held_prices)["total_equity"]
                held_summary = engine.summary(held_prices)
                drawdown_pct = (
                    (window_start_equity - held_summary["total_equity"]) / window_start_equity
                    if window_start_equity
                    else 0.0
                )
                if halted:
                    # Daily loss limit already tripped this window: stay in cash, no re-entry.
                    selected_symbols = held_symbols
                    prices = held_prices
                    event = "halted"
                    rebalance_reason = "daily_loss_halt"
                elif drawdown_pct >= self.config.daily_loss_limit_pct:
                    _liquidate_positions(engine, held_prices, held_symbols)
                    halted = True
                    selected_symbols = held_symbols
                    prices = held_prices
                    event = "daily_loss_halt"
                    rebalance_reason = "daily_loss_limit"
                    rebalance_history = _append_rebalance_history(
                        rebalance_history,
                        _rebalance_event(event, rebalance_reason, now, [], selected),
                    )
                else:
                    # Trailing take-profit (ratchets peak, exits on give-back) +
                    # hard stop-loss from entry. Trailing binds once a position runs up.
                    trailed = _apply_trailing_stop(
                        engine, held_prices, self.config.trailing_stop_pct
                    )
                    stopped = _apply_stop_loss(engine, held_prices, self.config.stop_loss_pct)
                    exited = trailed or stopped
                    if _should_intraday_rebalance(
                        now=now,
                        last_rebalanced_at=last_rebalanced_at,
                        held_symbols=held_symbols,
                        selected_symbols=selected_symbols,
                        market_snapshot=market_snapshot,
                        min_minutes=self.config.intraday_rebalance_min_minutes,
                        min_score_improvement=self.config.intraday_score_improvement,
                    ):
                        # Preserve realized PnL (incl. any stop-loss above) before the
                        # rebuild discards the engine ledger.
                        window_realized_pnl += engine.summary(held_prices)["realized_pnl"]
                        engine = self._build_confirmed_engine(
                            selected_symbols, held_summary["total_equity"], prices,
                            self.config.selection_limit,
                        )
                        event = "intraday_rebalanced"
                        rebalance_reason = "intraday_candidate_rotation"
                        last_rebalanced_at = now.astimezone(KST).isoformat()
                        rebalance_history = _append_rebalance_history(
                            rebalance_history,
                            _rebalance_event(event, rebalance_reason, now, selected_symbols, selected),
                        )
                    else:
                        selected_symbols = held_symbols
                        prices = held_prices
                        if trailed:
                            event = rebalance_reason = "trailing_stop"
                        elif stopped:
                            event = rebalance_reason = "stop_loss"
                        else:
                            event, rebalance_reason = "updated", "hold"

        engine_summary = engine.summary(prices)
        total_window_realized = window_realized_pnl + engine_summary["realized_pnl"]
        summary = {
            **engine_summary,
            "realized_pnl": total_window_realized,
            "window_realized_pnl": total_window_realized,
            "window_start_equity": window_start_equity,
        }
        self.store.save_state(
            self.config.run_id,
            {
                "run_id": self.config.run_id,
                "symbols": selected_symbols,
                "monitored_symbol_count": len(market_snapshot),
                "candidate_symbols": [candidate.symbol for candidate in selected],
                "candidates": [candidate.__dict__ for candidate in selected],
                "provider_stats": getattr(self.price_provider, "stats", {}),
                "last_rebalanced_at": last_rebalanced_at,
                "rebalance_reason": rebalance_reason,
                "rebalance_history": rebalance_history,
                "window_start": window_start_iso,
                "window_end": window_end.isoformat(),
                "window_start_equity": window_start_equity,
                "window_realized_pnl": window_realized_pnl,
                "halted": halted,
                "engine": engine.to_dict(),
                "last_prices": prices,
                "last_summary": summary,
                "last_positions": _visible_positions(engine.position_details(prices)),
                "updated_at": now.astimezone(KST).isoformat(),
            },
        )
        return {"event": event, "summary": summary, "prices": prices}

    def _build_confirmed_engine(
        self,
        confirmed_symbols: list[str],
        total_capital: float,
        prices: dict[str, float],
        slot_count: int,
    ) -> PaperLabEngine:
        """Equal-weight engine that buys only confirmed symbols.

        Capital is split into ``slot_count`` equal slots. Each confirmed symbol
        fills one slot; unfilled slots stay in the reserved cash bucket. With no
        confirmer, ``confirmed_symbols`` already equals the top selection, so all
        slots fill and the cash bucket is empty (legacy full-invest behaviour).
        """
        slot_count = max(slot_count, 1)
        per_slot = total_capital / slot_count
        filled = [s for s in confirmed_symbols if s in prices][:slot_count]
        buckets: dict[str, dict] = {
            sym: {"cash": per_slot, "position": None, "trades": []} for sym in filled
        }
        buckets[CASH_BUCKET] = {
            "cash": total_capital - per_slot * len(filled),
            "position": None,
            "trades": [],
        }
        engine = PaperLabEngine.from_dict({"buckets": buckets})
        for sym in filled:
            engine.buy(sym, price=prices[sym])
        return engine

    async def _confirm_symbols(self, symbols: list[str]) -> list[str]:
        """Return symbols passing the entry confirmer, capped at selection_limit.

        Without a confirmer, returns the top selection_limit symbols unchanged.
        """
        # Regime gate: in a downtrend (market leader below its EMA) hold cash —
        # no NEW entries. Existing positions stay managed by stop/daily-limit.
        if self.config.regime_enabled and not await self._is_risk_on():
            return []
        limit = self.config.selection_limit
        if self.confirmer is None:
            return symbols[:limit]
        confirmed: list[str] = []
        for symbol in symbols:
            if len(confirmed) >= limit:
                break
            df = await self._fetch_confirmation_ohlcv(symbol)
            if self.confirmer.confirm(symbol, df):
                confirmed.append(symbol)
        return confirmed

    async def _fetch_confirmation_ohlcv(self, symbol: str):
        getter = getattr(self.price_provider, "get_ohlcv", None)
        if getter is None:
            return None
        return await getter(
            symbol, self.config.confirm_timeframe, self.config.confirm_history_limit
        )

    async def _is_risk_on(self) -> bool:
        """True if the regime leader (BTC) closes above its EMA. Fail-open: if
        regime data is unavailable, do not block trading (return True)."""
        getter = getattr(self.price_provider, "get_ohlcv", None)
        if getter is None:
            return True
        df = await getter(
            self.config.regime_symbol,
            self.config.regime_timeframe,
            self.config.regime_history_limit,
        )
        period = self.config.regime_ema_period
        if not isinstance(df, pd.DataFrame) or "close" not in df or len(df) < period:
            return True
        close = df["close"]
        ema = close.ewm(span=period, adjust=False).mean()
        return bool(close.iloc[-1] > ema.iloc[-1])


def _prices_for_symbols(
    market_snapshot: list[MarketCandidate], symbols: list[str]
) -> dict[str, float]:
    prices_by_symbol = {candidate.symbol: candidate.price for candidate in market_snapshot}
    return {symbol: prices_by_symbol[symbol] for symbol in symbols}


def _visible_positions(details: list[dict]) -> list[dict]:
    """Hide the internal reserved cash bucket from reported positions."""
    return [d for d in details if d.get("symbol") != CASH_BUCKET]


def _liquidate_positions(engine: PaperLabEngine, prices: dict[str, float], symbols: list[str]) -> None:
    """Sell every open position among ``symbols`` at its mark price (realizes PnL)."""
    for symbol in symbols:
        bucket = engine.state.buckets.get(symbol)
        if bucket is not None and bucket.position is not None:
            bucket.sell(prices[symbol])


def _apply_stop_loss(
    engine: PaperLabEngine, prices: dict[str, float], stop_loss_pct: float
) -> bool:
    """Liquidate positions whose return breaches -stop_loss_pct. Returns True if any sold."""
    if stop_loss_pct <= 0:
        return False
    threshold = -abs(stop_loss_pct) * 100  # position_details return_pct is in percent
    stopped = False
    for detail in engine.position_details(prices):
        if detail.get("position_open") and detail["return_pct"] <= threshold:
            symbol = detail["symbol"]
            engine.state.buckets[symbol].sell(prices[symbol])
            stopped = True
    return stopped


def _apply_trailing_stop(
    engine: PaperLabEngine, prices: dict[str, float], trailing_pct: float
) -> bool:
    """Ratchet each open position's peak to the mark, then liquidate any whose
    price has fallen >= trailing_pct from that peak. Returns True if any sold."""
    if trailing_pct <= 0:
        return False
    exited = False
    for symbol, bucket in engine.state.buckets.items():
        pos = bucket.position
        if pos is None or symbol not in prices:
            continue
        mark = prices[symbol]
        if mark > pos.peak_price:
            pos.peak_price = mark
        if pos.peak_price > 0 and mark <= pos.peak_price * (1 - trailing_pct):
            bucket.sell(mark)
            exited = True
    return exited


def _should_intraday_rebalance(
    *,
    now: datetime,
    last_rebalanced_at: str | None,
    held_symbols: list[str],
    selected_symbols: list[str],
    market_snapshot: list[MarketCandidate],
    min_minutes: int,
    min_score_improvement: float,
) -> bool:
    if not last_rebalanced_at or held_symbols == selected_symbols:
        return False
    last_rebalanced = datetime.fromisoformat(last_rebalanced_at)
    elapsed_minutes = (now.astimezone(KST) - last_rebalanced.astimezone(KST)).total_seconds() / 60
    if elapsed_minutes < min_minutes:
        return False
    scored_snapshot = select_top_markets(
        market_snapshot,
        limit=len(market_snapshot),
        min_quote_volume=0,
    )
    scores = {candidate.symbol: candidate.score for candidate in scored_snapshot}
    selected_score = _average_score(selected_symbols, scores)
    held_score = _average_score(held_symbols, scores)
    if held_score <= 0:
        return selected_score > 0
    return selected_score >= held_score * (1 + min_score_improvement)


def _average_score(symbols: list[str], scores: dict[str, float]) -> float:
    if not symbols:
        return 0.0
    return sum(scores.get(symbol, 0.0) for symbol in symbols) / len(symbols)


def _rebalance_event(
    event: str,
    reason: str,
    now: datetime,
    symbols: list[str],
    candidates: list[MarketCandidate],
) -> dict:
    return {
        "event": event,
        "reason": reason,
        "at": now.astimezone(KST).isoformat(),
        "symbols": symbols,
        "candidate_symbols": [candidate.symbol for candidate in candidates],
    }


def _append_rebalance_history(history: list[dict], event: dict) -> list[dict]:
    return [*history, event][-20:]
