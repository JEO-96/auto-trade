from __future__ import annotations

import asyncio
import logging
import time

from core.data_fetcher import DataFetcher
from core.paper_lab.runtime import PaperLabConfig, PaperLabRuntime
from core.paper_lab.selector import MarketCandidate
from core.paper_lab.store import SqlAlchemyPaperLabStore

logger = logging.getLogger(__name__)

# Refresh the KRW universe periodically so new listings enter and delisted codes
# drop out without a server restart. Upbit rejects a fetch_tickers batch with a
# 404 "Code not found" if even one requested code is stale, so a stale cache
# would otherwise break every tick until restart.
SYMBOL_CACHE_TTL_SECONDS = 6 * 3600
UPBIT_TICKER_BATCH_SIZE = 100


def _is_unknown_market_error(exc: Exception) -> bool:
    """True when Upbit rejected the request because a market code is unknown
    (e.g. a delisted coin still in our cached symbol list)."""
    message = str(exc)
    return "Code not found" in message or '"name":404' in message


class UpbitTickerPriceProvider:
    def __init__(self, db_factory=None) -> None:
        self.fetcher = DataFetcher(exchange_id="upbit")
        self.db_factory = db_factory
        self._krw_symbols: list[str] | None = None
        self._krw_symbols_loaded_at: float = 0.0
        self.stats = {
            "market_load_calls": 0,
            "ticker_calls": 0,
            "ohlcv_calls": 0,
            "last_error": None,
        }

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int):
        """Fetch candle history for one symbol (DB-cached). Returns DataFrame or None."""
        loop = asyncio.get_running_loop()
        self.stats["ohlcv_calls"] += 1

        def _fetch():
            if self.db_factory is not None:
                with self.db_factory() as db:
                    return self.fetcher.fetch_ohlcv(symbol, timeframe, limit=limit, db=db)
            return self.fetcher.fetch_ohlcv(symbol, timeframe, limit=limit)

        try:
            return await loop.run_in_executor(None, _fetch)
        except Exception as exc:
            self.stats["last_error"] = str(exc)
            return None

    async def get_market_snapshot(self) -> list[MarketCandidate]:
        loop = asyncio.get_running_loop()
        symbols = await self._get_krw_symbols(loop)
        self.stats["ticker_calls"] += 1
        try:
            tickers = await loop.run_in_executor(None, lambda: self._fetch_tickers_batched(symbols))
            self.stats["last_error"] = None
        except Exception as exc:
            # A single bad code makes Upbit 404 the whole batch. This happens for
            # delisted coins (dropped by a market reload) AND for coins under
            # trading suspension (still listed in /market/all, so a reload keeps
            # them). Reload to pick up delistings, then fetch resiliently so any
            # remaining bad code is isolated and skipped instead of failing the
            # tick. Lets the lab self-heal without a restart.
            if _is_unknown_market_error(exc):
                self.stats["last_error"] = str(exc)
                logger.warning("[PaperLab] bad market code in ticker batch; reloading universe and refetching: %s", exc)
                symbols = await self._get_krw_symbols(loop, force_reload=True)
                tickers = await self._fetch_tickers_skipping_unknown(loop, symbols)
                self.stats["last_error"] = None
            else:
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

    async def _fetch_tickers_skipping_unknown(self, loop, symbols: list[str]) -> dict:
        """Fetch tickers for ``symbols``, dropping any code Upbit rejects with a
        404 "Code not found". Tries the whole batch first (one request when all
        codes are valid) and only bisects to isolate bad codes on failure, so the
        cost is O(bad * log n) extra requests rather than one-per-symbol."""
        if not symbols:
            return {}
        try:
            return await loop.run_in_executor(None, lambda: self._fetch_tickers_batched(symbols))
        except Exception as exc:
            if not _is_unknown_market_error(exc):
                raise
            if len(symbols) == 1:
                logger.warning("[PaperLab] skipping unknown market code: %s", symbols[0])
                return {}
            mid = len(symbols) // 2
            left = await self._fetch_tickers_skipping_unknown(loop, symbols[:mid])
            right = await self._fetch_tickers_skipping_unknown(loop, symbols[mid:])
            return {**left, **right}

    async def _get_krw_symbols(self, loop, force_reload: bool = False) -> list[str]:
        fresh = (
            self._krw_symbols is not None
            and not force_reload
            and (time.monotonic() - self._krw_symbols_loaded_at) < SYMBOL_CACHE_TTL_SECONDS
        )
        if fresh:
            return self._krw_symbols
        self.stats["market_load_calls"] += 1
        try:
            if force_reload:
                # reload=True bypasses ccxt's in-memory markets cache so delisted
                # codes are actually dropped (a plain call returns the stale set).
                markets = await loop.run_in_executor(None, lambda: self.fetcher.exchange.load_markets(True))
            else:
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
        self._krw_symbols_loaded_at = time.monotonic()
        return self._krw_symbols

    def _fetch_tickers_batched(self, symbols: list[str]) -> dict:
        tickers: dict = {}
        for i in range(0, len(symbols), UPBIT_TICKER_BATCH_SIZE):
            batch = symbols[i : i + UPBIT_TICKER_BATCH_SIZE]
            tickers.update(self.fetcher.exchange.fetch_tickers(batch))
        return tickers


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
    from core.paper_lab.confirmation import StrategyConfirmer

    # Phase 2: simplified to trend_rider_4h_v1 only — multi-year validation showed
    # it is the robust component (momentum_aggressive_4h was crash-fragile: 2022
    # -45%, 2025 -13%). Exits now include a native 5% trailing take-profit plus the
    # Phase 1 stop-loss / daily loss limit / regime gate / cash-when-no-signal.
    runtime = PaperLabRuntime(
        PaperLabConfig(),
        UpbitTickerPriceProvider(db_factory=db_factory),
        SqlAlchemyPaperLabStore(db_factory),
        confirmer=StrategyConfirmer("trend_rider_4h_v1"),
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
