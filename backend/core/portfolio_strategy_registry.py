"""포트폴리오(다자산) 전략 레지스트리.

기존 단일 심볼 전략(`core.strategy.STRATEGY_MAP`)과 분리.

명명된 프리셋:
  - dual_momentum_etf_v1: 069500/360750 + 153130, sequential 평가, 12M (현 운영)
  - dual_momentum_etf_v2: 069500/360750 + 153130, best_momentum (Antonacci 정합), 12M
  - dual_momentum_etf_kr_v1: 069500 + 153130 (2자산, 장기 백테스트용), sequential, 12M
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from core.strategies.portfolio import DualMomentumStrategy

# 프리셋 정의 — 이름 → 기본 파라미터
_PRESETS: Dict[str, Dict] = {
    "dual_momentum_etf_v1": {
        "risk_assets": ["069500", "360750"],
        "defensive_asset": "153130",
        "lookback_months": 12,
        "evaluation_mode": "sequential",
    },
    "dual_momentum_etf_v2": {
        "risk_assets": ["069500", "360750"],
        "defensive_asset": "153130",
        "lookback_months": 12,
        "evaluation_mode": "best_momentum",
    },
    "dual_momentum_etf_kr_v1": {
        "risk_assets": ["069500"],
        "defensive_asset": "153130",
        "lookback_months": 12,
        "evaluation_mode": "sequential",
    },
}


def list_portfolio_strategies() -> List[str]:
    return list(_PRESETS.keys())


def get_portfolio_strategy(
    name: str,
    *,
    lookback_months: Optional[int] = None,
    evaluation_mode: Optional[str] = None,
) -> DualMomentumStrategy:
    """이름으로 포트폴리오 전략 인스턴스 생성.

    선택 인자(lookback_months, evaluation_mode)는 프리셋의 값을 오버라이드.
    """
    preset = _PRESETS.get(name)
    if preset is None:
        raise ValueError(
            f"Unknown portfolio strategy: {name!r}. "
            f"Available: {list_portfolio_strategies()}"
        )
    params = dict(preset)
    if lookback_months is not None:
        params["lookback_months"] = int(lookback_months)
    if evaluation_mode is not None:
        params["evaluation_mode"] = evaluation_mode
    return DualMomentumStrategy(**params)


# 하위 호환 alias — 기존 import 위치에서 호출자가 dict 접근하던 경우 대비
PORTFOLIO_STRATEGIES = {name: DualMomentumStrategy for name in _PRESETS}
