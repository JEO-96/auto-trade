from core.strategies.momentum_breakout_basic import MomentumBreakoutBasicStrategy
from core.strategies.momentum_breakout_pro_stable import MomentumBreakoutProStableStrategy
from core.strategies.momentum_breakout_pro_aggressive import MomentumBreakoutProAggressiveStrategy
from core.strategies.momentum_breakout_elite import MomentumBreakoutEliteStrategy
from core.strategies.steady_compounder import SteadyCompounderStrategy
from core.strategies.steady_compounder_v1 import SteadyCompounderV1Strategy

# Timeframe-optimized strategies (성능 검증 완료)
from core.strategies.momentum_basic_1d import MomentumBasic1DStrategy
from core.strategies.momentum_stable_1h import MomentumStable1hStrategy
from core.strategies.momentum_stable_1d import MomentumStable1dStrategy
from core.strategies.momentum_aggressive_1h import MomentumAggressive1hStrategy
from core.strategies.momentum_aggressive_4h import MomentumAggressive4hStrategy
from core.strategies.momentum_aggressive_1d import MomentumAggressive1dStrategy
from core.strategies.momentum_elite_1d import MomentumElite1dStrategy
from core.strategies.steady_compounder_4h import SteadyCompounder4hStrategy

# Strategy name -> class mapping
STRATEGY_MAP = {
    # Original strategies
    "james_pro_elite": MomentumBreakoutEliteStrategy,
    "momentum_elite": MomentumBreakoutEliteStrategy,
    "james_pro_stable": MomentumBreakoutProStableStrategy,
    "momentum_stable": MomentumBreakoutProStableStrategy,
    "james_pro_aggressive": MomentumBreakoutProAggressiveStrategy,
    "momentum_aggressive": MomentumBreakoutProAggressiveStrategy,
    "steady_compounder": SteadyCompounderStrategy,
    "steady_compounder_v1": SteadyCompounderV1Strategy,

    # Timeframe-optimized (8개 — 성능 검증 통과)
    "momentum_basic_1d": MomentumBasic1DStrategy,
    "momentum_stable_1h": MomentumStable1hStrategy,
    "momentum_stable_1d": MomentumStable1dStrategy,
    "momentum_aggressive_1h": MomentumAggressive1hStrategy,
    "momentum_aggressive_4h": MomentumAggressive4hStrategy,
    "momentum_aggressive_1d": MomentumAggressive1dStrategy,
    "momentum_elite_1d": MomentumElite1dStrategy,
    "steady_compounder_4h": SteadyCompounder4hStrategy,
}

DEFAULT_STRATEGY = "momentum_stable"


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
