"""주식(KOSPI/KOSDAQ ETF/종목) OHLCV fetcher.

- pykrx 기반, 일봉 전용 (v1)
- DB 캐싱: ohlcv_data 테이블 재사용 (market='stock', timeframe='1d')
- SQLite 테스트 호환을 위해 PostgreSQL 전용 upsert 미사용 → select-then-insert/update fallback
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

MARKET = "stock"
TIMEFRAME = "1d"


class StockDataFetcher:
    """pykrx 기반 한국 주식/ETF 일봉 fetcher.

    pykrx는 모듈 import 시점에 무거운 의존성을 끌어오므로,
    실제 fetch 호출 시 lazy import한다 (테스트에서 mock하기 쉽게).
    """

    def __init__(self) -> None:
        self.market = MARKET
        self.timeframe = TIMEFRAME

    # ─────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────

    def fetch_ohlcv(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        db: Session | None = None,
    ) -> pd.DataFrame:
        """주식 OHLCV(일봉) fetch.

        Args:
            symbol: 종목 코드 (예: "069500")
            start_date: "YYYY-MM-DD"
            end_date:   "YYYY-MM-DD"
            db: SQLAlchemy 세션. 주어지면 DB 캐싱.

        Returns:
            DataFrame[timestamp(datetime), open, high, low, close, volume]
            거래일 없으면 빈 DataFrame.
        """
        start_dt = pd.Timestamp(start_date).normalize()
        end_dt = pd.Timestamp(end_date).normalize()
        if end_dt < start_dt:
            return self._empty_df()

        # DB 미사용 → 바로 pykrx 호출
        if db is None:
            return self._fetch_from_pykrx(symbol, start_dt, end_dt)

        # ── DB 캐시 로직 ──
        cached_df = self._load_from_db(db, symbol, start_dt, end_dt)
        cached_dates = set(cached_df["timestamp"].dt.normalize().tolist()) if not cached_df.empty else set()

        # 빠진 영업일 구간 계산 — KRX 거래일은 pykrx 호출 결과로만 알 수 있어,
        # 보수적으로 캐시된 마지막 날짜 다음날부터 end_dt까지 다시 fetch한다.
        # 단순화: 캐시가 비었거나 end_dt가 캐시 마지막보다 뒤면 그 차이 구간만 fetch.
        fetch_ranges = self._compute_missing_ranges(cached_df, start_dt, end_dt)

        if fetch_ranges:
            for fs, fe in fetch_ranges:
                logger.info("StockDataFetcher: pykrx fetch %s %s~%s", symbol, fs.date(), fe.date())
                fresh = self._fetch_from_pykrx(symbol, fs, fe)
                if not fresh.empty:
                    self._save_to_db(db, symbol, fresh)

            # 캐시 다시 로드
            cached_df = self._load_from_db(db, symbol, start_dt, end_dt)

        return cached_df

    # ─────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def _fetch_from_pykrx(
        self,
        symbol: str,
        start_dt: pd.Timestamp,
        end_dt: pd.Timestamp,
    ) -> pd.DataFrame:
        """pykrx에서 OHLCV 조회. ETF / 일반 종목 모두 시도."""
        try:
            from pykrx import stock as pykrx_stock  # type: ignore
        except Exception as e:
            logger.error("pykrx import 실패: %s", e)
            return self._empty_df()

        s = start_dt.strftime("%Y%m%d")
        e = end_dt.strftime("%Y%m%d")

        df: pd.DataFrame | None = None
        # ETF 우선
        try:
            df = pykrx_stock.get_etf_ohlcv_by_date(s, e, symbol)
        except Exception as exc:
            logger.debug("get_etf_ohlcv_by_date 실패(%s): %s — 일반 종목으로 재시도", symbol, exc)
            df = None

        if df is None or df.empty:
            try:
                df = pykrx_stock.get_market_ohlcv_by_date(s, e, symbol)
            except Exception as exc:
                logger.error("pykrx get_market_ohlcv_by_date 실패(%s): %s", symbol, exc)
                return self._empty_df()

        if df is None or df.empty:
            return self._empty_df()

        return self._normalize_pykrx_df(df)

    @staticmethod
    def _normalize_pykrx_df(df: pd.DataFrame) -> pd.DataFrame:
        """pykrx의 한글 컬럼을 영문으로 변환.

        ETF / 일반 종목 모두 시가/고가/저가/종가/거래량 컬럼을 가진다.
        """
        rename_map = {
            "시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume",
            # ETF 추가 컬럼은 무시
        }
        out = df.rename(columns=rename_map).copy()
        keep = ["open", "high", "low", "close", "volume"]
        for col in keep:
            if col not in out.columns:
                out[col] = 0.0
        out = out[keep]
        out.index = pd.to_datetime(out.index)
        out = out.reset_index().rename(columns={"index": "timestamp", "날짜": "timestamp"})
        # 인덱스 컬럼명이 자동 'index'/'날짜' 어느 쪽이든 처리
        if "timestamp" not in out.columns:
            out = out.rename(columns={out.columns[0]: "timestamp"})
        out["timestamp"] = pd.to_datetime(out["timestamp"])
        for col in ["open", "high", "low", "close", "volume"]:
            out[col] = out[col].astype(float)
        out = out.sort_values("timestamp").reset_index(drop=True)
        return out[["timestamp", "open", "high", "low", "close", "volume"]]

    def _load_from_db(
        self,
        db: Session,
        symbol: str,
        start_dt: pd.Timestamp,
        end_dt: pd.Timestamp,
    ) -> pd.DataFrame:
        start_ms = self._to_ms(start_dt)
        end_ms = self._to_ms(end_dt + timedelta(days=1))  # inclusive

        rows = (
            db.query(models.OHLCV)
            .filter(
                models.OHLCV.market == MARKET,
                models.OHLCV.symbol == symbol,
                models.OHLCV.timeframe == TIMEFRAME,
                models.OHLCV.timestamp >= start_ms,
                models.OHLCV.timestamp < end_ms,
            )
            .order_by(models.OHLCV.timestamp.asc())
            .all()
        )
        if not rows:
            return self._empty_df()

        data = [
            {
                "timestamp": pd.to_datetime(int(r.timestamp), unit="ms"),
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume),
            }
            for r in rows
        ]
        return pd.DataFrame(data)

    def _save_to_db(self, db: Session, symbol: str, df: pd.DataFrame) -> None:
        """SQLite/PostgreSQL 호환 select-then-insert/update."""
        if df.empty:
            return

        saved = 0
        try:
            for _, row in df.iterrows():
                ts_ms = self._to_ms(pd.Timestamp(row["timestamp"]))
                existing = (
                    db.query(models.OHLCV)
                    .filter(
                        models.OHLCV.market == MARKET,
                        models.OHLCV.symbol == symbol,
                        models.OHLCV.timeframe == TIMEFRAME,
                        models.OHLCV.timestamp == ts_ms,
                    )
                    .first()
                )
                if existing is None:
                    db.add(
                        models.OHLCV(
                            market=MARKET,
                            symbol=symbol,
                            timeframe=TIMEFRAME,
                            timestamp=ts_ms,
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                        )
                    )
                else:
                    existing.open = float(row["open"])
                    existing.high = float(row["high"])
                    existing.low = float(row["low"])
                    existing.close = float(row["close"])
                    existing.volume = float(row["volume"])
                saved += 1
            db.commit()
            logger.info("StockDataFetcher: saved %d rows for %s", saved, symbol)
        except Exception as exc:
            db.rollback()
            logger.error("StockDataFetcher save 실패: %s", exc)

    @staticmethod
    def _to_ms(ts: pd.Timestamp | datetime) -> int:
        if isinstance(ts, datetime) and not isinstance(ts, pd.Timestamp):
            ts = pd.Timestamp(ts)
        return int(pd.Timestamp(ts).value // 10**6)

    @staticmethod
    def _compute_missing_ranges(
        cached_df: pd.DataFrame,
        start_dt: pd.Timestamp,
        end_dt: pd.Timestamp,
    ) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
        """캐시에서 빠진 구간 추정.

        v1은 단순화: 캐시가 비어있으면 [start, end] 1구간,
        있으면 [start, 첫 캐시 일자), (마지막 캐시 일자, end] 두 구간.
        주말/공휴일 구분은 안 함 — pykrx가 자체적으로 거래일만 반환.
        """
        if cached_df.empty:
            return [(start_dt, end_dt)]

        first_cached = pd.Timestamp(cached_df["timestamp"].iloc[0]).normalize()
        last_cached = pd.Timestamp(cached_df["timestamp"].iloc[-1]).normalize()

        ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        if start_dt < first_cached:
            ranges.append((start_dt, first_cached - timedelta(days=1)))
        if last_cached < end_dt:
            ranges.append((last_cached + timedelta(days=1), end_dt))
        return ranges
