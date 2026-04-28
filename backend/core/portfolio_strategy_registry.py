"""포트폴리오(다자산) 전략 레지스트리.

기존 단일 심볼 전략(`core.strategy.STRATEGY_MAP`)과 분리.
"""
from __future__ import annotations

from core.strategies.portfolio import DualMomentumStrategy

PORTFOLIO_STRATEGIES = {
    "dual_momentum_etf_v1": DualMomentumStrategy,
}


def get_portfolio_strategy(name: str):
    """이름으로 포트폴리오 전략 인스턴스 생성."""
    cls = PORTFOLIO_STRATEGIES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown portfolio strategy: {name!r}. "
            f"Available: {list(PORTFOLIO_STRATEGIES.keys())}"
        )
    return cls()
