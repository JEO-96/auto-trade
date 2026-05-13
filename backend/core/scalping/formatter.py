from __future__ import annotations

from .types import SignalDecision


def _money(value: float) -> str:
    return f"{int(round(value)):,}원"


def _number(value: float) -> str:
    return f"{int(round(value)):,}"


def format_signal_alert(decision: SignalDecision) -> str:
    if decision.levels is None:
        raise ValueError("levels are required for alert formatting")

    levels = decision.levels
    reasons = "\n".join(f"- {reason}" for reason in decision.reasons)
    return (
        f"[초단타 {decision.grade}급 후보] {decision.name} / {decision.symbol}\n\n"
        f"진입가: {_number(levels.entry_low)} ~ {_money(levels.entry_high)}\n"
        f"손절가: {_money(levels.stop)} (-{levels.risk_pct:.2f}%)\n"
        f"1차 매도: {_money(levels.target1)} (+{levels.reward1_pct:.2f}%, 1R)\n"
        f"2차 매도: {_money(levels.target2)} (+{levels.reward2_pct:.2f}%, 1.8R)\n\n"
        f"근거:\n{reasons}\n\n"
        f"무효:\n{_money(levels.stop)} 이탈 또는 {levels.invalidation_reason} 하회 지속\n\n"
        "주의:\n조건부 시나리오이며 수익을 보장하지 않습니다."
    )
