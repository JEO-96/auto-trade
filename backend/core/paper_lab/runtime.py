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
        else:
            engine = PaperLabEngine.from_dict(state_doc["engine"])
            previous_window_start = state_doc["window_start"]
            held_symbols = list(engine.state.buckets.keys())
            held_prices = _prices_for_symbols(market_snapshot, held_symbols)
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
            else:
                selected_symbols = held_symbols
                prices = held_prices
                event = "updated"

        summary = engine.summary(prices)
        self.store.save_state(
            self.config.run_id,
            {
                "run_id": self.config.run_id,
                "symbols": selected_symbols,
                "monitored_symbol_count": len(market_snapshot),
                "candidate_symbols": [candidate.symbol for candidate in selected],
                "candidates": [candidate.__dict__ for candidate in selected],
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
