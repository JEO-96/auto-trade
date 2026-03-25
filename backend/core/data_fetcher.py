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
    def __init__(self, exchange_id: str = None):
        # Initialize exchange instance (공개 데이터용 — API 키 불필요)
        eid = exchange_id or config.EXCHANGE_ID
        exchange_class = getattr(ccxt, eid)
        self.exchange_id = eid
        self.exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True,
        })

    def fetch_ohlcv(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT, start_date=None, end_date=None, db: Session = None):
        """
        Fetches OHLCV data. DB가 제공되면 캐시를 활용:
        1. since~until 범위에서 있어야 할 캔들 타임스탬프 목록 생성
        2. DB에 이미 있는 타임스탬프 조회
        3. 빠진 타임스탬프가 있으면 해당 구간만 API fetch + DB insert
        4. 빠진 게 없으면 DB 데이터 그대로 반환
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

            # DB 캐시 미사용 → 바로 API fetch
            if not db or not since:
                ohlcv = self._fetch_from_api_robust(symbol, timeframe, limit if not since else None, since, until)
                if not ohlcv:
                    return None
                return self._to_dataframe(ohlcv, limit, start_date)

            # ── DB 캐시 로직 ──

            # 1. 있어야 할 타임스탬프 목록 생성 (since부터 until까지, duration_ms 간격)
            expected_timestamps: set[int] = set()
            ts = (since // duration_ms) * duration_ms  # since를 캔들 경계로 정렬
            while ts <= until:
                expected_timestamps.add(ts)
                ts += duration_ms

            # 2. DB에 있는 타임스탬프 조회
            db_records = db.query(models.OHLCV).filter(
                models.OHLCV.symbol == symbol,
                models.OHLCV.timeframe == timeframe,
                models.OHLCV.timestamp >= since,
                models.OHLCV.timestamp <= until,
            ).order_by(models.OHLCV.timestamp.asc()).all()

            existing_timestamps: set[int] = {r.timestamp for r in db_records}

            # 3. 빠진 타임스탬프 확인
            missing_timestamps = expected_timestamps - existing_timestamps

            if not missing_timestamps:
                # DB에 전부 있음 → 그대로 반환
                logger.info("DB cache complete for %s %s (%d candles). No API call needed.",
                           symbol, timeframe, len(db_records))
                ohlcv = [[r.timestamp, r.open, r.high, r.low, r.close, r.volume] for r in db_records]
                return self._to_dataframe(ohlcv, limit, start_date)

            # 4. 빠진 구간 계산 → 연속 구간으로 묶어서 API fetch
            missing_sorted = sorted(missing_timestamps)
            gaps = self._find_gaps(missing_sorted, duration_ms)

            logger.info("DB cache for %s %s: %d/%d candles cached, %d missing in %d gap(s). Fetching...",
                       symbol, timeframe, len(existing_timestamps), len(expected_timestamps),
                       len(missing_timestamps), len(gaps))

            # 5. Gap 구간 API fetch + DB 저장
            for gap_since, gap_until in gaps:
                api_data = self._fetch_from_api_robust(symbol, timeframe, None, gap_since, gap_until)
                if api_data:
                    self._save_to_db(db, symbol, timeframe, api_data)

            # 6. DB에서 최종 데이터 로드
            db_records = db.query(models.OHLCV).filter(
                models.OHLCV.symbol == symbol,
                models.OHLCV.timeframe == timeframe,
                models.OHLCV.timestamp >= since,
                models.OHLCV.timestamp <= until,
            ).order_by(models.OHLCV.timestamp.asc()).all()

            ohlcv = [[r.timestamp, r.open, r.high, r.low, r.close, r.volume] for r in db_records]
            logger.info("Loaded %d candles from DB for %s %s after gap fill.", len(ohlcv), symbol, timeframe)

            if not ohlcv:
                return None
            return self._to_dataframe(ohlcv, limit, start_date)

        except Exception as e:
            logger.error("Error fetching data: %s", e)
            return None

    def _to_dataframe(self, ohlcv: list, limit: int | None, start_date: str | None) -> pd.DataFrame | None:
        """OHLCV 리스트를 DataFrame으로 변환."""
        if not ohlcv:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        # 중복 제거 (혹시 모를 경우)
        df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
        if limit and not start_date:
            df = df.tail(limit)
        return df

    @staticmethod
    def _find_gaps(missing_sorted: list[int], duration_ms: int) -> list[tuple[int, int]]:
        """빠진 타임스탬프 리스트를 연속 구간(gap)으로 묶는다."""
        if not missing_sorted:
            return []
        gaps: list[tuple[int, int]] = []
        gap_start = missing_sorted[0]
        prev = missing_sorted[0]
        for ts in missing_sorted[1:]:
            if ts - prev > duration_ms:
                # 이전 연속 구간 종료
                gaps.append((gap_start, prev + duration_ms))
                gap_start = ts
            prev = ts
        # 마지막 구간
        gaps.append((gap_start, prev + duration_ms))
        return gaps

    async def fetch_ohlcv_async(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT, start_date=None, end_date=None, db: Session = None):
        """
        Async wrapper for fetch_ohlcv. Runs the blocking fetch in a thread pool
        executor so that time.sleep() calls inside _fetch_from_api_robust() do not
        block the event loop.
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
                chunk_size = FETCH_CHUNK_SIZE_UPBIT if self.exchange_id == 'upbit' else FETCH_CHUNK_SIZE_DEFAULT
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
        Bulk-upserts candles to DB using PostgreSQL INSERT ... ON CONFLICT DO UPDATE.
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
                stmt = pg_insert(models.OHLCV).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timeframe', 'timestamp'],
                    set_={
                        'open': stmt.excluded.open,
                        'high': stmt.excluded.high,
                        'low': stmt.excluded.low,
                        'close': stmt.excluded.close,
                        'volume': stmt.excluded.volume,
                    },
                )
                db.execute(stmt)
                db.commit()
                total_saved += len(rows)
            logger.info("Saved %d candles to DB cache for %s %s.", total_saved, symbol, timeframe)
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
