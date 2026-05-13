from core.scalping.formatter import format_signal_alert
from core.scalping.types import PriceLevels, SignalDecision


def test_format_signal_alert_contains_prices_and_risk_language():
    decision = SignalDecision(
        symbol="005930",
        name="삼성전자",
        should_alert=True,
        score=86,
        grade="A",
        reasons=["거래대금 급증", "VWAP 상회", "체결강도 우위"],
        rejections=[],
        levels=PriceLevels(
            entry_low=70100,
            entry_high=70300,
            stop=69500,
            target1=70900,
            target2=71600,
            risk_pct=0.99,
            reward1_pct=1.0,
            reward2_pct=2.0,
            invalidation_reason="VWAP",
        ),
    )

    message = format_signal_alert(decision)

    assert "[초단타 A급 후보]" in message
    assert "진입가: 70,100 ~ 70,300원" in message
    assert "손절가: 69,500원" in message
    assert "1차 매도: 70,900원" in message
    assert "조건부 시나리오" in message
