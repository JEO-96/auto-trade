from __future__ import annotations

import asyncio
import logging

from core.data_fetcher import DataFetcher
from core.paper_lab.runtime import PaperLabConfig, PaperLabRuntime
from core.paper_lab.store import SqlAlchemyPaperLabStore

logger = logging.getLogger(__name__)


class UpbitTickerPriceProvider:
    def __init__(self) -> None:
        self.fetcher = DataFetcher(exchange_id="upbit")

    async def get_prices(self, symbols: list[str]) -> dict[str, float]:
        loop = asyncio.get_running_loop()
        prices: dict[str, float] = {}
        for symbol in symbols:
            ticker = await loop.run_in_executor(
                None, lambda s=symbol: self.fetcher.exchange.fetch_ticker(s)
            )
            price = float(ticker.get("last") or ticker.get("close") or 0)
            if price <= 0:
                raise ValueError(f"Invalid ticker price for {symbol}: {price}")
            prices[symbol] = price
        return prices


class PaperLabService:
    def __init__(self, runtime: PaperLabRuntime, poll_seconds: int = 300) -> None:
        self.runtime = runtime
        self.poll_seconds = poll_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="paper-lab-service")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                result = await self.runtime.tick()
                logger.info(
                    "[PaperLab] %s equity=%.0f open_positions=%d",
                    result["event"],
                    result["summary"]["total_equity"],
                    result["summary"]["open_position_count"],
                )
            except Exception:
                logger.exception("[PaperLab] tick failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                pass


def build_paper_lab_service(db_factory, poll_seconds: int = 300) -> PaperLabService:
    runtime = PaperLabRuntime(
        PaperLabConfig(),
        UpbitTickerPriceProvider(),
        SqlAlchemyPaperLabStore(db_factory),
    )
    return PaperLabService(runtime, poll_seconds=poll_seconds)
