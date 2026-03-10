import asyncio
import ccxt
import logging
import pandas as pd
import time
from core import config
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
import models

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        # Initialize exchange instance
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True,
        })

    def fetch_ohlcv(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT, start_date=None, end_date=None, db: Session = None):
        """
        Fetches OHLCV data with Database Caching.
        Steps:
        1. Try to load requested range from DB.
        2. Identify gaps or fetch missing data from API.
        3. Save new data to DB.

        NOTE: This is a blocking method. Call it via fetch_ohlcv_async() from async
        contexts, or wrap with asyncio.to_thread() at the call site, to avoid
        blocking the event loop during the time.sleep() calls inside
        _fetch_from_api_robust().
        """
        try:
            since = None
            until = None

            if start_date:
                since = self.exchange.parse8601(f"{start_date}T00:00:00Z")
            if end_date:
                until = self.exchange.parse8601(f"{end_date}T23:59:59Z")

            # If no start_date, determine roughly based on limit
            if not since and limit:
                # Estimate since based on limit and current time
                duration = self.exchange.parse_timeframe(timeframe) * 1000
                since = self.exchange.milliseconds() - (duration * (limit + 10)) # safety margin

            # 1. Check DB Cache
            db_data = []
            if db:
                query = db.query(models.OHLCV).filter(
                    models.OHLCV.symbol == symbol,
                    models.OHLCV.timeframe == timeframe,
                    models.OHLCV.timestamp >= since
                )
                if until:
                    query = query.filter(models.OHLCV.timestamp <= until)

                db_records = query.order_by(models.OHLCV.timestamp.asc()).all()
                db_data = [[r.timestamp, r.open, r.high, r.low, r.close, r.volume] for r in db_records]

            # 2. Decide if we need to fetch more
            ohlcv = db_data

            # Simplified Logic: If no DB data or data is insufficient, fetch everything from API for that range
            # In a production app, we would fetch only the GAPS.
            if len(ohlcv) < (limit if limit else 10):
                logger.info("Cache miss for %s %s. Fetching from exchange...", symbol, timeframe)
                # Use existing robust fetch logic
                ohlcv_api = self._fetch_from_api_robust(symbol, timeframe, limit, since, until)

                if ohlcv_api and db:
                    # Save newly fetched data to DB
                    self._save_to_db(db, symbol, timeframe, ohlcv_api)

                ohlcv = ohlcv_api
            else:
                logger.info("Loading %d candles from DB cache for %s %s.", len(ohlcv), symbol, timeframe)

            if not ohlcv: return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            # Final trim for limit
            if limit and not start_date:
                df = df.tail(limit)

            return df
        except Exception as e:
            logger.error("Error fetching data: %s", e)
            return None

    async def fetch_ohlcv_async(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT, start_date=None, end_date=None, db: Session = None):
        """
        Async wrapper for fetch_ohlcv. Runs the blocking fetch in a thread pool
        executor so that time.sleep() calls inside _fetch_from_api_robust() do not
        block the event loop.

        Usage from async bot loop:
            df = await fetcher.fetch_ohlcv_async(symbol, timeframe, limit, db=db)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.fetch_ohlcv(symbol, timeframe, limit, start_date, end_date, db)
        )

    def _fetch_from_api_robust(self, symbol, timeframe, limit, since, until):
        """
        Blocking method: contains time.sleep() for rate limiting.
        Must not be called directly from the async event loop.
        Use fetch_ohlcv_async() instead.
        """
        ohlcv = []
        try:
            # Re-use logic for date-range vs limit
            if since and not limit:
                current_since = since
                target_until = until if until else self.exchange.milliseconds()
                while current_since < target_until:
                    try:
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=200)
                        if not batch: break
                        last_timestamp = batch[-1][0]
                        current_since = last_timestamp + 1
                        ohlcv.extend(batch)
                        if last_timestamp >= target_until: break
                        time.sleep(max(0.2, self.exchange.rateLimit / 1000))
                    except Exception as e:
                        if "too_many_requests" in str(e).lower(): time.sleep(5); continue
                        break
            else:
                # Limit based backward fetch
                limit = limit or config.LIMIT
                chunk_size = 200 if config.EXCHANGE_ID == 'upbit' else 500
                last_since = None
                while len(ohlcv) < limit:
                    fetch_limit = min(chunk_size, limit - len(ohlcv))
                    if last_since is None:
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, limit=fetch_limit)
                    else:
                        duration = self.exchange.parse_timeframe(timeframe) * 1000
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, since=last_since - (duration * fetch_limit), limit=fetch_limit)
                    if not batch: break
                    ohlcv = batch + ohlcv
                    last_since = batch[0][0]
                    time.sleep(max(0.2, self.exchange.rateLimit / 1000))
            return ohlcv
        except Exception as e:
            logger.error("API fetch error: %s", e)
            return []

    def _save_to_db(self, db: Session, symbol: str, timeframe: str, data: list):
        """
        Bulk-upserts candles to DB using PostgreSQL INSERT ... ON CONFLICT DO NOTHING.
        Replaces the previous per-candle SELECT + INSERT loop (N+1 queries) with a
        single bulk statement, which is significantly faster for large batches.
        Requires the uq_ohlcv_symbol_tf_ts unique constraint on (symbol, timeframe, timestamp).
        """
        if not data:
            return
        try:
            rows = [
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": candle[0],
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                }
                for candle in data
            ]
            stmt = pg_insert(models.OHLCV).values(rows).on_conflict_do_nothing(
                index_elements=['symbol', 'timeframe', 'timestamp']
            )
            db.execute(stmt)
            db.commit()
            logger.info("Saved up to %d new candles to DB cache (duplicates skipped).", len(rows))
        except Exception as e:
            db.rollback()
            logger.error("Failed to save OHLCV to DB: %s", e)

if __name__ == "__main__":
    # Test Data Fetcher
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv()
    if df is not None:
        logger.info("Successfully fetched %d candles for %s.", len(df), config.SYMBOL)
        logger.info("\n%s", df.tail())
