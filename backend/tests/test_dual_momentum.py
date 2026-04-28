"""DualMomentumStrategy 단위 테스트.

룰:
  1) 한국 모멘텀 > 단기채 → 069500 100%
  2) 한국 미충족 + 미국 모멘텀 > 단기채 → 360750 100%
  3) 둘 다 미충족 → 153130 100%
  4) 데이터 부족 → 153130 100% (방어)
"""
from __future__ import annotations

import pandas as pd
import pytest

from core.strategies.portfolio.dual_momentum import DualMomentumStrategy


def _make_df(start: str, end: str, start_price: float, end_price: float) -> pd.DataFrame:
    """선형 가격 변화 시계열 (영업일 기준 daily)."""
    idx = pd.date_range(start=start, end=end, freq="B")  # business days
    n = len(idx)
    if n == 0:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    closes = pd.Series(
        [start_price + (end_price - start_price) * i / max(n - 1, 1) for i in range(n)],
        index=idx,
    )
    return pd.DataFrame({
        "timestamp": idx,
        "open": closes.values,
        "high": closes.values,
        "low": closes.values,
        "close": closes.values,
        "volume": [1_000_000] * n,
    })


def test_kr_momentum_wins():
    """한국 ETF 12M 수익률이 단기채보다 높으면 069500 100%."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")
    start = "2023-12-01"
    end = "2024-12-31"

    df_dict = {
        "069500": _make_df(start, end, 100, 130),  # +30%
        "360750": _make_df(start, end, 100, 110),  # +10%
        "153130": _make_df(start, end, 100, 105),  # +5%
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 1.0, "360750": 0.0, "153130": 0.0}


def test_us_momentum_wins_when_kr_loses():
    """한국이 단기채에 못 미치고 미국이 단기채를 이기면 360750 100%."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")
    start = "2023-12-01"
    end = "2024-12-31"

    df_dict = {
        "069500": _make_df(start, end, 100, 100),  # +0%
        "360750": _make_df(start, end, 100, 120),  # +20%
        "153130": _make_df(start, end, 100, 105),  # +5%
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 0.0, "360750": 1.0, "153130": 0.0}


def test_defensive_when_both_lose():
    """한국/미국 모두 단기채에 못 미치면 153130 100%."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")
    start = "2023-12-01"
    end = "2024-12-31"

    df_dict = {
        "069500": _make_df(start, end, 100, 100),
        "360750": _make_df(start, end, 100, 102),
        "153130": _make_df(start, end, 100, 105),
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 0.0, "360750": 0.0, "153130": 1.0}


def test_defensive_when_all_risk_assets_lookback_unavailable():
    """방어자산은 데이터 충분하지만 모든 위험자산 lookback 불가 → 153130."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")

    short_start = "2024-12-01"  # 1개월치 → 12M lookback 불가
    short_end = "2024-12-31"

    df_dict = {
        "069500": _make_df(short_start, short_end, 100, 130),
        "360750": _make_df(short_start, short_end, 100, 130),
        "153130": _make_df("2023-12-01", "2024-12-31", 100, 105),  # 단기채만 충분
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 0.0, "360750": 0.0, "153130": 1.0}


def test_defensive_when_defensive_asset_lookback_unavailable():
    """방어자산(153130) 자체의 lookback이 불가하면 안전하게 153130으로 폴백."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")

    df_dict = {
        "069500": _make_df("2023-12-01", "2024-12-31", 100, 130),
        "360750": _make_df("2023-12-01", "2024-12-31", 100, 130),
        "153130": _make_df("2024-12-01", "2024-12-31", 100, 105),  # 방어자산 데이터 부족
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 0.0, "360750": 0.0, "153130": 1.0}


def test_kr_selected_when_us_data_missing_but_kr_beats_defensive():
    """360750 데이터 부족이지만 069500이 단기채를 이기면 069500 선택.

    실제 상황: 360750(TIGER S&P500)이 2020년 상장 → 2015~2021 구간에서
    069500은 데이터 충분, 360750은 부족. 이 경우 069500을 무시하지 말고
    069500 vs 153130 비교를 진행해야 한다.
    """
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")

    df_dict = {
        "069500": _make_df("2023-12-01", "2024-12-31", 100, 130),  # +30%
        "360750": pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"]),
        "153130": _make_df("2023-12-01", "2024-12-31", 100, 105),  # +5%
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 1.0, "360750": 0.0, "153130": 0.0}


def test_us_selected_when_kr_data_missing_but_us_beats_defensive():
    """069500 데이터 부족이고 360750이 단기채를 이기면 360750 선택."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")

    df_dict = {
        "069500": _make_df("2024-12-01", "2024-12-31", 100, 130),  # 데이터 부족
        "360750": _make_df("2023-12-01", "2024-12-31", 100, 120),  # +20%
        "153130": _make_df("2023-12-01", "2024-12-31", 100, 105),  # +5%
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 0.0, "360750": 1.0, "153130": 0.0}


def test_defensive_when_kr_data_missing_and_us_loses():
    """069500 데이터 부족 + 360750은 단기채에 못 미침 → 153130."""
    strategy = DualMomentumStrategy()
    eval_date = pd.Timestamp("2024-12-31")

    df_dict = {
        "069500": _make_df("2024-12-01", "2024-12-31", 100, 130),  # 데이터 부족
        "360750": _make_df("2023-12-01", "2024-12-31", 100, 102),  # +2%
        "153130": _make_df("2023-12-01", "2024-12-31", 100, 105),  # +5%
    }
    weights = strategy.compute_weights(df_dict, eval_date)
    assert weights == {"069500": 0.0, "360750": 0.0, "153130": 1.0}
