from __future__ import annotations

import asyncio
import logging

from core.data_fetcher import DataFetcher
from core.paper_lab.runtime import PaperLabConfig, PaperLabRuntime
from core.paper_lab.selector import MarketCandidate
from core.paper_lab.store import SqlAlchemyPaperLabStore

logger = logging.getLogger(__name__)


class UpbitTickerPriceProvider:
    def __init__(self) -> None:
        self.fetcher = DataFetcher(exchange_id="upbit")
        self._krw_symbols: list[str] | None = None
        self.stats = {
            "market_load_calls": 0,
            "ticker_calls": 0,
            "last_error": None,
        }

    async def get_market_snapshot(self) -> list[MarketCandidate]:
        loop = asyncio.get_running_loop()
        symbols = await self._get_krw_symbols(loop)
        self.stats["ticker_calls"] += 1
        try:
            tickers = await loop.run_in_executor(None, lambda: self.fetcher.exchange.fetch_tickers(symbols))
            self.stats["last_error"] = None
        except Exception as exc:
            self.stats["last_error"] = str(exc)
            raise
        candidates: list[MarketCandidate] = []
        for symbol, ticker in tickers.items():
            price = float(ticker.get("last") or ticker.get("close") or 0)
            quote_volume = _quote_volume(ticker, price)
            percentage = float(ticker.get("percentage") or 0)
            if price > 0:
                candidates.append(
                    MarketCandidate(
                        symbol=symbol,
                        price=price,
                        quote_volume=quote_volume,
                        percentage=percentage,
                    )
                )
        return candidates

    async def _get_krw_symbols(self, loop) -> list[str]:
        if self._krw_symbols is not None:
            return self._krw_symbols
        self.stats["market_load_calls"] += 1
        try:
            markets = await loop.run_in_executor(None, self.fetcher.exchange.load_markets)
            self.stats["last_error"] = None
        except Exception as exc:
            self.stats["last_error"] = str(exc)
            raise
        self._krw_symbols = [
            symbol
            for symbol, market in markets.items()
            if symbol.endswith("/KRW") and market.get("active", True)
        ]
        return self._krw_symbols


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


def _quote_volume(ticker: dict, price: float) -> float:
    quote_volume = ticker.get("quoteVolume")
    if quote_volume is not None:
        return float(quote_volume)
    base_volume = ticker.get("baseVolume")
    if base_volume is not None:
        return float(base_volume) * price
    return 0.0
