"""StockDataFetcher 단위 테스트.

- pykrx 호출은 mock
- DB 캐싱 동작 확인 (SQLite in-memory)
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from core.stock_data_fetcher import StockDataFetcher
import models


def _pykrx_like_df(start: str, end: str, start_price: float, end_price: float) -> pd.DataFrame:
    """pykrx 반환과 유사한 형태(한글 컬럼, DatetimeIndex)."""
    idx = pd.date_range(start=start, end=end, freq="B")
    n = len(idx)
    closes = [start_price + (end_price - start_price) * i / max(n - 1, 1) for i in range(n)]
    df = pd.DataFrame({
        "시가": closes,
        "고가": closes,
        "저가": closes,
        "종가": closes,
        "거래량": [1_000_000] * n,
    }, index=idx)
    df.index.name = "날짜"
    return df


def test_first_call_fetches_from_pykrx_and_saves_to_db(db_session):
    """첫 호출 시 pykrx에서 받아 DB에 저장."""
    fetcher = StockDataFetcher()
    fake = _pykrx_like_df("2024-01-01", "2024-01-31", 100, 110)

    with patch("pykrx.stock.get_etf_ohlcv_by_date", return_value=fake) as mock_etf:
        df = fetcher.fetch_ohlcv("069500", "2024-01-01", "2024-01-31", db=db_session)

    assert not df.empty
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert mock_etf.called

    # DB에 저장됐는지
    rows = db_session.query(models.OHLCV).filter(
        models.OHLCV.market == "stock",
        models.OHLCV.symbol == "069500",
    ).all()
    assert len(rows) == len(fake)
    assert all(r.timeframe == "1d" for r in rows)


def test_second_call_uses_db_cache(db_session):
    """두 번째 호출은 DB 캐시에서 반환 — pykrx 호출 안 됨."""
    fetcher = StockDataFetcher()
    fake = _pykrx_like_df("2024-01-01", "2024-01-31", 100, 110)

    with patch("pykrx.stock.get_etf_ohlcv_by_date", return_value=fake):
        fetcher.fetch_ohlcv("069500", "2024-01-01", "2024-01-31", db=db_session)

    # 두 번째 호출: pykrx mock이 호출되지 않아야 함
    with patch("pykrx.stock.get_etf_ohlcv_by_date") as mock_etf, \
         patch("pykrx.stock.get_market_ohlcv_by_date") as mock_market:
        df = fetcher.fetch_ohlcv("069500", "2024-01-01", "2024-01-31", db=db_session)
        assert not mock_etf.called, "두 번째 호출에서 ETF API가 호출되면 안 됨 (캐시 hit 기대)"
        assert not mock_market.called

    assert not df.empty
    assert len(df) == len(fake)


def test_no_db_session_returns_data_without_caching():
    """db=None이면 단순 fetch만 수행 (DB 저장 없음)."""
    fetcher = StockDataFetcher()
    fake = _pykrx_like_df("2024-01-01", "2024-01-31", 100, 110)

    with patch("pykrx.stock.get_etf_ohlcv_by_date", return_value=fake):
        df = fetcher.fetch_ohlcv("069500", "2024-01-01", "2024-01-31", db=None)

    assert not df.empty
    assert len(df) == len(fake)


def test_etf_lookup_falls_back_to_market_ohlcv(db_session):
    """ETF API가 빈 결과면 일반 종목 API로 fallback."""
    fetcher = StockDataFetcher()
    empty_df = pd.DataFrame(columns=["시가", "고가", "저가", "종가", "거래량"])
    market_df = _pykrx_like_df("2024-01-01", "2024-01-31", 50, 55)

    with patch("pykrx.stock.get_etf_ohlcv_by_date", return_value=empty_df), \
         patch("pykrx.stock.get_market_ohlcv_by_date", return_value=market_df) as mock_market:
        df = fetcher.fetch_ohlcv("005930", "2024-01-01", "2024-01-31", db=db_session)

    assert mock_market.called
    assert not df.empty
    assert len(df) == len(market_df)


def test_invalid_date_range_returns_empty():
    """end < start면 빈 DataFrame."""
    fetcher = StockDataFetcher()
    df = fetcher.fetch_ohlcv("069500", "2024-12-31", "2024-01-01", db=None)
    assert df.empty
