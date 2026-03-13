import asyncio
import ccxt
import logging
import pandas as pd
import time
from core import config
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
import models
from constants import (
    FETCH_CHUNK_SIZE_UPBIT,
    FETCH_CHUNK_SIZE_DEFAULT,
    DB_SAVE_CHUNK_SIZE,
    FETCH_MAX_RETRIES,
    FETCH_BACKOFF_MAX_SECONDS,
)

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
        Fetches OHLCV data with smart gap-filling DB cache.
        1. Load cached data from DB for the requested range.
        2. Identify missing gaps (before/after cached range).
        3. Fetch only the missing parts from API and save to DB.
        4. Reload complete data from DB.
        """
        try:
            since = None
            until = None

            if start_date:
                since = self.exchange.parse8601(f"{start_date}T00:00:00Z")
            if end_date:
                until = self.exchange.parse8601(f"{end_date}T23:59:59Z")

            if not since and limit:
                duration = self.exchange.parse_timeframe(timeframe) * 1000
                since = self.exchange.milliseconds() - (duration * (limit + 10))

            if not until:
                until = self.exchange.milliseconds()

            duration_ms = self.exchange.parse_timeframe(timeframe) * 1000

            # 1. DB 캐시 조회
            db_data = []
            if db and since:
                query = db.query(models.OHLCV).filter(
                    models.OHLCV.symbol == symbol,
                    models.OHLCV.timeframe == timeframe,
                    models.OHLCV.timestamp >= since,
                    models.OHLCV.timestamp <= until,
                ).order_by(models.OHLCV.timestamp.asc())
                db_records = query.all()
                db_data = [[r.timestamp, r.open, r.high, r.low, r.close, r.volume] for r in db_records]

            # 2. 캐시 충분 여부 판단 및 gap 식별
            expected_count = int((until - since) / duration_ms) if since else (limit or 100)
            gaps = []

            if len(db_data) >= expected_count * 0.9:
                # 캐시가 충분하지만, 끝 부분이 오래됐으면 최신 데이터만 보충
                if db_data:
                    last_ts = db_data[-1][0]
                    if until - last_ts > duration_ms * 2:
                        gaps.append((last_ts + 1, until))
                        logger.info("Cache tail gap for %s %s: fetching %s ~ end",
                                   symbol, timeframe, pd.Timestamp(last_ts + 1, unit='ms'))
                if not gaps:
                    logger.info("Loading %d candles from DB cache for %s %s.", len(db_data), symbol, timeframe)
                    ohlcv = db_data
                else:
                    ohlcv = db_data
            else:
                # 캐시 부족 → 빠진 구간 계산
                if not db_data:
                    # 캐시 전무: 전체 구간 fetch
                    gaps.append((since, until))
                    logger.info("No cache for %s %s. Fetching full range from exchange...", symbol, timeframe)
                else:
                    first_ts = db_data[0][0]
                    last_ts = db_data[-1][0]
                    # 앞쪽 gap
                    if first_ts - since > duration_ms * 2:
                        gaps.append((since, first_ts - 1))
                        logger.info("Cache head gap for %s %s: %s ~ %s",
                                   symbol, timeframe,
                                   pd.Timestamp(since, unit='ms'), pd.Timestamp(first_ts, unit='ms'))
                    # 뒤쪽 gap
                    if until - last_ts > duration_ms * 2:
                        gaps.append((last_ts + 1, until))
                        logger.info("Cache tail gap for %s %s: %s ~ %s",
                                   symbol, timeframe,
                                   pd.Timestamp(last_ts, unit='ms'), pd.Timestamp(until, unit='ms'))
                    # 캐시가 너무 적으면 전체 재fetch
                    if len(db_data) < expected_count * 0.5 and not gaps:
                        gaps.append((since, until))
                        logger.info("Cache too sparse for %s %s (have %d, need %d). Full refetch.",
                                   symbol, timeframe, len(db_data), expected_count)
                ohlcv = db_data

            # 3. Gap 구간 API fetch + DB 저장
            for gap_since, gap_until in gaps:
                logger.info("Fetching gap for %s %s: %s ~ %s",
                           symbol, timeframe,
                           pd.Timestamp(gap_since, unit='ms'), pd.Timestamp(gap_until, unit='ms'))
                api_data = self._fetch_from_api_robust(symbol, timeframe, None, gap_since, gap_until)
                if api_data:
                    if db:
                        self._save_to_db(db, symbol, timeframe, api_data)
                    ohlcv.extend(api_data)

            # 4. Gap을 채운 후 DB에서 최종 데이터 재로드 (정렬 + 중복 제거)
            if gaps and db and since:
                db_records = db.query(models.OHLCV).filter(
                    models.OHLCV.symbol == symbol,
                    models.OHLCV.timeframe == timeframe,
                    models.OHLCV.timestamp >= since,
                    models.OHLCV.timestamp <= until,
                ).order_by(models.OHLCV.timestamp.asc()).all()
                ohlcv = [[r.timestamp, r.open, r.high, r.low, r.close, r.volume] for r in db_records]
                logger.info("Reloaded %d candles from DB after gap fill for %s %s.", len(ohlcv), symbol, timeframe)
            elif gaps:
                # DB 없이 메모리에서 정렬 + 중복 제거
                seen = set()
                unique = []
                for c in sorted(ohlcv, key=lambda x: x[0]):
                    if c[0] not in seen:
                        seen.add(c[0])
                        unique.append(c)
                ohlcv = unique

            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

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
                retry_count = 0
                while current_since < target_until:
                    try:
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=FETCH_CHUNK_SIZE_UPBIT)
                        if not batch: break
                        last_timestamp = batch[-1][0]
                        current_since = last_timestamp + 1
                        ohlcv.extend(batch)
                        retry_count = 0
                        if last_timestamp >= target_until: break
                        time.sleep(max(0.3, self.exchange.rateLimit / 1000))
                    except Exception as e:
                        if "too_many_requests" in str(e).lower():
                            retry_count += 1
                            if retry_count > FETCH_MAX_RETRIES:
                                logger.warning("Max retries reached for %s %s, returning %d candles fetched so far.", symbol, timeframe, len(ohlcv))
                                break
                            wait_time = min(2 ** retry_count, FETCH_BACKOFF_MAX_SECONDS)
                            logger.info("Rate limited, waiting %ds (retry %d/%d)...", wait_time, retry_count, FETCH_MAX_RETRIES)
                            time.sleep(wait_time)
                            continue
                        break
            else:
                # Limit based backward fetch
                limit = limit or config.LIMIT
                chunk_size = FETCH_CHUNK_SIZE_UPBIT if config.EXCHANGE_ID == 'upbit' else FETCH_CHUNK_SIZE_DEFAULT
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
        대용량 데이터는 1000개씩 청크로 나눠서 저장.
        """
        if not data:
            return
        chunk_size = DB_SAVE_CHUNK_SIZE
        total_saved = 0
        try:
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
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
                    for candle in chunk
                ]
                stmt = pg_insert(models.OHLCV).values(rows).on_conflict_do_nothing(
                    index_elements=['symbol', 'timeframe', 'timestamp']
                )
                db.execute(stmt)
                db.commit()
                total_saved += len(rows)
            logger.info("Saved %d candles to DB cache for %s %s (duplicates skipped).", total_saved, symbol, timeframe)
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
