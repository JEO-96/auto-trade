from core.strategies.momentum_breakout_basic import MomentumBreakoutBasicStrategy
from core.strategies.momentum_breakout_pro_stable import MomentumBreakoutProStableStrategy
from core.strategies.momentum_breakout_pro_aggressive import MomentumBreakoutProAggressiveStrategy

def get_strategy(name="momentum_stable"):
    if name == "james_pro_stable" or name == "momentum_stable":
        return MomentumBreakoutProStableStrategy()
    if name == "james_pro_aggressive" or name == "momentum_aggressive":
        return MomentumBreakoutProAggressiveStrategy()
    return MomentumBreakoutBasicStrategy()

# Alias for backward compatibility
MomentumBreakoutStrategy = MomentumBreakoutBasicStrategy
