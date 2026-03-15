from core.strategies.momentum_breakout_basic import MomentumBreakoutBasicStrategy

# Timeframe-optimized strategies (15개 = 5 base × 3 timeframes)
from core.strategies.momentum_basic_1h import MomentumBasic1hStrategy
from core.strategies.momentum_basic_4h import MomentumBasic4hStrategy
from core.strategies.momentum_basic_1d import MomentumBasic1DStrategy

from core.strategies.momentum_stable_1h import MomentumStable1hStrategy
from core.strategies.momentum_stable_4h import MomentumStable4hStrategy
from core.strategies.momentum_stable_1d import MomentumStable1dStrategy

from core.strategies.momentum_aggressive_1h import MomentumAggressive1hStrategy
from core.strategies.momentum_aggressive_4h import MomentumAggressive4hStrategy
from core.strategies.momentum_aggressive_1d import MomentumAggressive1dStrategy

from core.strategies.momentum_elite_1h import MomentumElite1hStrategy
from core.strategies.momentum_elite_4h import MomentumElite4hStrategy
from core.strategies.momentum_elite_1d import MomentumElite1dStrategy

from core.strategies.steady_compounder_1h import SteadyCompounder1hStrategy
from core.strategies.steady_compounder_4h import SteadyCompounder4hStrategy
from core.strategies.steady_compounder_1d import SteadyCompounder1dStrategy

# Strategy name -> class mapping
STRATEGY_MAP = {
    # Legacy aliases (DB 하위 호환 — 기존 봇/백테스트 데이터 유지)
    "momentum_breakout_basic": MomentumBasic1DStrategy,
    "james_basic": MomentumBasic1DStrategy,
    "momentum_breakout_pro_stable": MomentumStable1hStrategy,
    "james_pro_stable": MomentumStable1hStrategy,
    "momentum_stable": MomentumStable1hStrategy,
    "momentum_breakout_pro_aggressive": MomentumAggressive1dStrategy,
    "james_pro_aggressive": MomentumAggressive1dStrategy,
    "momentum_aggressive": MomentumAggressive1dStrategy,
    "momentum_breakout_elite": MomentumElite1dStrategy,
    "james_pro_elite": MomentumElite1dStrategy,
    "momentum_elite": MomentumElite1dStrategy,
    "steady_compounder": SteadyCompounder4hStrategy,
    "steady_compounder_v1": SteadyCompounder4hStrategy,

    # 15개 타임프레임 최적화 전략 (5 base × 3 TF)
    "momentum_basic_1h": MomentumBasic1hStrategy,
    "momentum_basic_4h": MomentumBasic4hStrategy,
    "momentum_basic_1d": MomentumBasic1DStrategy,

    "momentum_stable_1h": MomentumStable1hStrategy,
    "momentum_stable_4h": MomentumStable4hStrategy,
    "momentum_stable_1d": MomentumStable1dStrategy,

    "momentum_aggressive_1h": MomentumAggressive1hStrategy,
    "momentum_aggressive_4h": MomentumAggressive4hStrategy,
    "momentum_aggressive_1d": MomentumAggressive1dStrategy,

    "momentum_elite_1h": MomentumElite1hStrategy,
    "momentum_elite_4h": MomentumElite4hStrategy,
    "momentum_elite_1d": MomentumElite1dStrategy,

    "steady_compounder_1h": SteadyCompounder1hStrategy,
    "steady_compounder_4h": SteadyCompounder4hStrategy,
    "steady_compounder_1d": SteadyCompounder1dStrategy,
}

DEFAULT_STRATEGY = "momentum_stable_1h"


def get_strategy(name: str = DEFAULT_STRATEGY):
    """
    Factory function: returns a strategy instance by name.
    Falls back to MomentumBreakoutBasicStrategy for unknown names.
    """
    strategy_cls = STRATEGY_MAP.get(name)
    if strategy_cls is not None:
        return strategy_cls()
    return MomentumBreakoutBasicStrategy()


# Alias for backward compatibility
MomentumBreakoutStrategy = MomentumBreakoutBasicStrategy
