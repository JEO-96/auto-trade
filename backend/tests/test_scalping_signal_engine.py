from core.scalping.config import ScalpingAlertConfig
from core.scalping.signal_engine import SignalEngine
from core.scalping.types import CandidateSnapshot


def _snapshot(**overrides):
    base = dict(
        symbol="005930",
        name="삼성전자",
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
    )
    base.update(overrides)
    return CandidateSnapshot(**base)


def test_signal_engine_alerts_only_high_quality_snapshot():
    decision = SignalEngine(ScalpingAlertConfig()).evaluate(_snapshot())

    assert decision.should_alert is True
    assert decision.grade == "A"
    assert decision.score >= 78
    assert decision.levels is not None
    assert "거래대금 급증" in decision.reasons


def test_signal_engine_rejects_low_liquidity():
    decision = SignalEngine(ScalpingAlertConfig()).evaluate(
        _snapshot(trading_value_5m=300_000_000, trading_value_ratio=1.1)
    )

    assert decision.should_alert is False
    assert "trading value too low" in decision.rejections


def test_signal_engine_rejects_wide_spread():
    decision = SignalEngine(ScalpingAlertConfig()).evaluate(_snapshot(bid=69000, ask=70200))

    assert decision.should_alert is False
    assert "spread too wide" in decision.rejections
