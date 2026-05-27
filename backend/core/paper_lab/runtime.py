from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from core.paper_lab.daily_window import KST, kst_daily_window
from core.paper_lab.engine import PaperLabEngine
from core.paper_lab.selector import MarketCandidate, select_top_markets


DEFAULT_RUN_ID = "paper_lab_market_scan_v1"
DEFAULT_SELECTION_LIMIT = 10
DEFAULT_MIN_QUOTE_VOLUME = 500_000_000.0
DEFAULT_INTRADAY_REBALANCE_MIN_MINUTES = 60
DEFAULT_INTRADAY_SCORE_IMPROVEMENT = 0.20


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


class PaperLabRuntime:
    def __init__(
        self,
        config: PaperLabConfig,
        price_provider: MarketDataProvider,
        store: PaperLabStore,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.price_provider = price_provider
        self.store = store
        self.now_fn = now_fn or (lambda: datetime.now(tz=KST))

    async def tick(self) -> dict:
        now = self.now_fn()
        window_start, window_end = kst_daily_window(now)
        window_start_iso = window_start.isoformat()
        market_snapshot = await self.price_provider.get_market_snapshot()
        selected = select_top_markets(
            market_snapshot,
            limit=self.config.selection_limit,
            min_quote_volume=self.config.min_quote_volume,
        )
        selected_symbols = [candidate.symbol for candidate in selected]
        prices = {candidate.symbol: candidate.price for candidate in selected}
        state_doc = self.store.load_state(self.config.run_id)

        if state_doc is None:
            engine = self._build_fully_invested_engine(
                selected_symbols, self.config.total_capital, prices
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
        else:
            engine = PaperLabEngine.from_dict(state_doc["engine"])
            previous_window_start = state_doc["window_start"]
            held_symbols = list(engine.state.buckets.keys())
            held_prices = _prices_for_symbols(market_snapshot, held_symbols)
            rebalance_reason = state_doc.get("rebalance_reason", "hold")
            rebalance_history = state_doc.get("rebalance_history", [])
            last_rebalanced_at = state_doc.get("last_rebalanced_at") or state_doc.get("updated_at")
            if previous_window_start != window_start_iso:
                previous_summary = engine.summary(held_prices)
                self.store.save_snapshot(
                    self.config.run_id,
                    {
                        "window_start": previous_window_start,
                        "window_end": window_start_iso,
                        "summary": previous_summary,
                        "prices": held_prices,
                        "candidate_symbols": [candidate.symbol for candidate in selected],
                        "created_at": now.astimezone(KST).isoformat(),
                    },
                )
                engine = self._build_fully_invested_engine(
                    selected_symbols, previous_summary["total_equity"], prices
                )
                event = "daily_rebalanced"
                rebalance_reason = "daily_window_rotation"
                last_rebalanced_at = now.astimezone(KST).isoformat()
                rebalance_history = _append_rebalance_history(
                    rebalance_history,
                    _rebalance_event(event, rebalance_reason, now, selected_symbols, selected),
                )
            else:
                held_summary = engine.summary(held_prices)
                if _should_intraday_rebalance(
                    now=now,
                    last_rebalanced_at=last_rebalanced_at,
                    held_symbols=held_symbols,
                    selected_symbols=selected_symbols,
                    market_snapshot=market_snapshot,
                    min_minutes=self.config.intraday_rebalance_min_minutes,
                    min_score_improvement=self.config.intraday_score_improvement,
                ):
                    engine = self._build_fully_invested_engine(
                        selected_symbols, held_summary["total_equity"], prices
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
                    event = "updated"
                    rebalance_reason = "hold"

        summary = engine.summary(prices)
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
                "engine": engine.to_dict(),
                "last_prices": prices,
                "last_summary": summary,
                "updated_at": now.astimezone(KST).isoformat(),
            },
        )
        return {"event": event, "summary": summary, "prices": prices}

    def _build_fully_invested_engine(
        self, symbols: list[str], total_capital: float, prices: dict[str, float]
    ) -> PaperLabEngine:
        engine = PaperLabEngine(symbols, total_capital)
        for symbol in symbols:
            engine.buy(symbol, price=prices[symbol])
        return engine


def _prices_for_symbols(
    market_snapshot: list[MarketCandidate], symbols: list[str]
) -> dict[str, float]:
    prices_by_symbol = {candidate.symbol: candidate.price for candidate in market_snapshot}
    return {symbol: prices_by_symbol[symbol] for symbol in symbols}


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
