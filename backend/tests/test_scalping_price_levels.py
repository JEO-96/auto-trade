from datetime import datetime, timezone

from core.scalping.config import ScalpingAlertConfig
from core.scalping.price_levels import calculate_price_levels, round_price_to_tick
from core.scalping.types import CandidateSnapshot


def _strong_snapshot() -> CandidateSnapshot:
    return CandidateSnapshot(
        symbol="005930",
        name="Samsung Electronics",
        price=70200,
        previous_close=69000,
        trading_value_5m=4_500_000_000,
        trading_value_ratio=4.2,
        volume_ratio=3.6,
        execution_strength=128.0,
        vwap=69600,
        intraday_high=70300,
        pivot_high=70000,
        pullback_low=69500,
        atr_1m=120,
        atr_3m=260,
        bid=70100,
        ask=70200,
        bid_depth=120_000,
        ask_depth=90_000,
        timestamp=datetime(2026, 5, 13, 9, 45, tzinfo=timezone.utc),
    )


def test_candidate_snapshot_computed_fields():
    snap = _strong_snapshot()

    assert round(snap.change_pct, 2) == 1.74
    assert round(snap.spread_pct, 3) == 0.142
    assert round(snap.orderbook_imbalance, 3) == 0.571


def test_default_config_is_strict():
    config = ScalpingAlertConfig()

    assert config.max_daily_alerts == 10
    assert config.min_score >= 75
    assert config.max_stop_pct == 3.0
    assert config.dry_run is True


def test_round_price_to_tick_floor_and_ceil():
    assert round_price_to_tick(70123, "floor") == 70100
    assert round_price_to_tick(70123, "ceil") == 70200
    assert round_price_to_tick(70123, "nearest") == 70100


def test_calculate_price_levels_uses_dynamic_stop_and_r_targets():
    levels, rejection = calculate_price_levels(_strong_snapshot(), ScalpingAlertConfig())

    assert rejection is None
    assert levels is not None
    assert levels.entry_low >= 70000
    assert levels.stop < levels.entry_low
    assert 0.6 <= levels.risk_pct <= 3.0
    assert levels.target1 > levels.entry_high
    assert levels.target2 > levels.target1
    assert "VWAP" in levels.invalidation_reason or "pullback" in levels.invalidation_reason


def test_calculate_price_levels_rejects_wide_stop():
    snap = _strong_snapshot()
    wide = CandidateSnapshot(
        **{
            **snap.__dict__,
            "pullback_low": 65000,
            "vwap": 65000,
            "pivot_high": 70000,
        }
    )

    levels, rejection = calculate_price_levels(wide, ScalpingAlertConfig(max_stop_pct=1.0))

    assert levels is None
    assert rejection == "stop distance too wide"
