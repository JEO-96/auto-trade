from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from core.paper_lab.daily_window import KST, kst_daily_window
from core.paper_lab.engine import PaperLabEngine


DEFAULT_RUN_ID = "paper_lab_equal_weight_v1"
DEFAULT_SYMBOLS = ["BTC/KRW", "ETH/KRW", "SOL/KRW", "XRP/KRW"]


class PriceProvider(Protocol):
    async def get_prices(self, symbols: list[str]) -> dict[str, float]:
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
    symbols: list[str] = field(default_factory=lambda: DEFAULT_SYMBOLS.copy())
    total_capital: float = 1_000_000.0
    run_id: str = DEFAULT_RUN_ID


class PaperLabRuntime:
    def __init__(
        self,
        config: PaperLabConfig,
        price_provider: PriceProvider,
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
        prices = await self.price_provider.get_prices(self.config.symbols)
        state_doc = self.store.load_state(self.config.run_id)

        if state_doc is None:
            engine = self._build_fully_invested_engine(self.config.total_capital, prices)
            event = "initialized"
        else:
            engine = PaperLabEngine.from_dict(state_doc["engine"])
            previous_window_start = state_doc["window_start"]
            if previous_window_start != window_start_iso:
                previous_summary = engine.summary(prices)
                self.store.save_snapshot(
                    self.config.run_id,
                    {
                        "window_start": previous_window_start,
                        "window_end": window_start_iso,
                        "summary": previous_summary,
                        "prices": prices,
                        "created_at": now.astimezone(KST).isoformat(),
                    },
                )
                engine = self._build_fully_invested_engine(previous_summary["total_equity"], prices)
                event = "daily_rebalanced"
            else:
                event = "updated"

        summary = engine.summary(prices)
        self.store.save_state(
            self.config.run_id,
            {
                "run_id": self.config.run_id,
                "symbols": self.config.symbols,
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
        self, total_capital: float, prices: dict[str, float]
    ) -> PaperLabEngine:
        engine = PaperLabEngine(self.config.symbols, total_capital)
        for symbol in self.config.symbols:
            engine.buy(symbol, price=prices[symbol])
        return engine
