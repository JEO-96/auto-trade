"""PortfolioBacktester 단위 테스트 — pykrx 네트워크 호출은 mock."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from core.portfolio_backtester import PortfolioBacktester


def _make_pykrx_df(start: str, end: str, start_price: float, end_price: float) -> pd.DataFrame:
    """pykrx 형식 DataFrame (한글 컬럼, DatetimeIndex)."""
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


def _build_pykrx_side_effect(price_specs: dict):
    """symbol별 가격 사양으로 pykrx mock side_effect 생성.

    price_specs = {"069500": (start_price, end_price), ...}
    """
    def _fn(start_str, end_str, symbol):
        start = pd.Timestamp(start_str).strftime("%Y-%m-%d")
        end = pd.Timestamp(end_str).strftime("%Y-%m-%d")
        sp, ep = price_specs.get(symbol, (100, 100))
        return _make_pykrx_df(start, end, sp, ep)
    return _fn


def test_run_returns_required_keys():
    """결과 dict에 필수 키 존재."""
    price_specs = {
        "069500": (100, 130),  # +30%
        "360750": (100, 110),  # +10%
        "153130": (100, 105),  # +5%
    }
    side_effect = _build_pykrx_side_effect(price_specs)

    with patch("pykrx.stock.get_etf_ohlcv_by_date", side_effect=side_effect):
        bt = PortfolioBacktester(commission_rate=0.001)
        result = bt.run(
            start_date="2022-01-01",
            end_date="2024-06-30",
            initial_capital=10_000_000,
            db=None,
        )

    required_keys = {
        "strategy_name", "assets", "initial_capital", "final_capital",
        "total_return", "cagr", "max_drawdown", "sharpe",
        "total_rebalances", "holding_periods",
        "equity_curve", "trades", "rebalance_log",
    }
    assert required_keys.issubset(result.keys())

    assert result["strategy_name"] == "dual_momentum_etf_v1"
    assert sorted(result["assets"]) == sorted(["069500", "360750", "153130"])
    assert result["initial_capital"] == 10_000_000


def test_run_field_types():
    """결과의 핵심 필드 타입 검증."""
    price_specs = {
        "069500": (100, 130),
        "360750": (100, 110),
        "153130": (100, 105),
    }
    with patch("pykrx.stock.get_etf_ohlcv_by_date", side_effect=_build_pykrx_side_effect(price_specs)):
        bt = PortfolioBacktester()
        result = bt.run("2022-01-01", "2024-06-30", 10_000_000, db=None)

    assert isinstance(result["final_capital"], float)
    assert isinstance(result["equity_curve"], list)
    assert all(isinstance(p, dict) and "time" in p and "value" in p for p in result["equity_curve"])
    assert isinstance(result["rebalance_log"], list)
    assert isinstance(result["trades"], list)
    assert isinstance(result["holding_periods"], dict)
    assert set(result["holding_periods"].keys()) == {"069500", "360750", "153130"}


def test_run_picks_korean_etf_when_kr_momentum_dominates():
    """한국 ETF가 가장 강할 때 069500이 주로 선택되어야 함."""
    price_specs = {
        "069500": (100, 200),  # +100%
        "360750": (100, 105),
        "153130": (100, 102),
    }
    with patch("pykrx.stock.get_etf_ohlcv_by_date", side_effect=_build_pykrx_side_effect(price_specs)):
        bt = PortfolioBacktester()
        result = bt.run("2022-01-01", "2024-06-30", 10_000_000, db=None)

    selected_assets = [r["selected_asset"] for r in result["rebalance_log"]]
    # 12M lookback이 잡히는 시점부터 069500이 선택되어야 함 (방어 → 069500 전환)
    assert "069500" in selected_assets


def test_run_uses_defensive_when_all_lose():
    """모든 자산이 단기채에 못 미치면 153130 보유."""
    price_specs = {
        "069500": (100, 95),
        "360750": (100, 95),
        "153130": (100, 110),
    }
    with patch("pykrx.stock.get_etf_ohlcv_by_date", side_effect=_build_pykrx_side_effect(price_specs)):
        bt = PortfolioBacktester()
        result = bt.run("2022-01-01", "2024-06-30", 10_000_000, db=None)

    selected_assets = [r["selected_asset"] for r in result["rebalance_log"]]
    # 모든 시점에서 153130
    assert all(a == "153130" for a in selected_assets), f"got: {set(selected_assets)}"


def test_run_with_invalid_date_range_raises():
    """end < start이면 ValueError."""
    bt = PortfolioBacktester()
    with pytest.raises(ValueError):
        bt.run(start_date="2024-12-31", end_date="2024-01-01", initial_capital=1_000_000, db=None)


def test_unknown_strategy_raises_value_error():
    """알 수 없는 전략명은 명확히 ValueError."""
    with pytest.raises(ValueError, match="Unknown portfolio strategy"):
        PortfolioBacktester(strategy_name="nonexistent_strategy_v999")


def test_total_rebalances_matches_log_length():
    price_specs = {"069500": (100, 130), "360750": (100, 105), "153130": (100, 102)}
    with patch("pykrx.stock.get_etf_ohlcv_by_date", side_effect=_build_pykrx_side_effect(price_specs)):
        bt = PortfolioBacktester()
        result = bt.run("2022-01-01", "2024-06-30", 10_000_000, db=None)

    assert result["total_rebalances"] == len(result["rebalance_log"])
