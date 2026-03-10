from core.strategies.momentum_breakout_basic import MomentumBreakoutBasicStrategy
from core.strategies.momentum_breakout_pro_stable import MomentumBreakoutProStableStrategy
from core.strategies.momentum_breakout_pro_aggressive import MomentumBreakoutProAggressiveStrategy
from core.strategies.momentum_breakout_elite import MomentumBreakoutEliteStrategy

# Strategy name -> class mapping
STRATEGY_MAP = {
    "james_pro_elite": MomentumBreakoutEliteStrategy,
    "momentum_elite": MomentumBreakoutEliteStrategy,
    "james_pro_stable": MomentumBreakoutProStableStrategy,
    "momentum_stable": MomentumBreakoutProStableStrategy,
    "james_pro_aggressive": MomentumBreakoutProAggressiveStrategy,
    "momentum_aggressive": MomentumBreakoutProAggressiveStrategy,
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
