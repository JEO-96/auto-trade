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

from core.strategies.multi_signal_1h import MultiSignal1hStrategy
from core.strategies.multi_signal_4h import MultiSignal4hStrategy
from core.strategies.multi_signal_1d import MultiSignal1dStrategy

from core.strategies.quick_swing_1h import QuickSwing1hStrategy
from core.strategies.trend_rider_4h import TrendRider4hStrategy
from core.strategies.wide_swing_1d import WideSwing1dStrategy

# 15분봉 전략
from core.strategies.scalper_15m import Scalper15mStrategy
from core.strategies.quick_swing_15m import QuickSwing15mStrategy
from core.strategies.multi_signal_15m import MultiSignal15mStrategy
from core.strategies.trend_follower_15m import TrendFollower15mStrategy
from core.strategies.signal_test_15m import SignalTest15mStrategy

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
    "momentum_breakout_elite": MultiSignal1dStrategy,
    "james_pro_elite": MultiSignal1dStrategy,
    "momentum_elite": MultiSignal1dStrategy,
    "steady_compounder": TrendRider4hStrategy,
    "steady_compounder_v1": TrendRider4hStrategy,
    "steady_compounder_4h": TrendRider4hStrategy,

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

    "momentum_elite_1h": MultiSignal1hStrategy,
    "momentum_elite_4h": MultiSignal4hStrategy,
    "momentum_elite_1d": MultiSignal1dStrategy,

    "multi_signal_1h": MultiSignal1hStrategy,
    "multi_signal_4h": MultiSignal4hStrategy,
    "multi_signal_1d": MultiSignal1dStrategy,

    "steady_compounder_1h": QuickSwing1hStrategy,
    "quick_swing_1h": QuickSwing1hStrategy,
    "trend_rider_4h": TrendRider4hStrategy,
    "steady_compounder_1d": WideSwing1dStrategy,
    "wide_swing_1d": WideSwing1dStrategy,

    # 15분봉 전략
    "scalper_15m": Scalper15mStrategy,
    "quick_swing_15m": QuickSwing15mStrategy,
    "multi_signal_15m": MultiSignal15mStrategy,
    "trend_follower_15m": TrendFollower15mStrategy,
    "signal_test_15m": SignalTest15mStrategy,
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


def apply_custom_params(strategy, custom_params: dict):
    """커스텀 파라미터를 전략 인스턴스에 적용"""
    if not custom_params:
        return

    param_map = {
        'rsi_period': 'rsi_period',
        'rsi_threshold': 'rsi_threshold',
        'adx_threshold': 'adx_threshold',
        'volume_multiplier': 'volume_multiplier',
        'macd_fast': 'macd_fast',
        'macd_slow': 'macd_slow',
        'macd_signal': 'macd_signal',
        'rsi_upper_limit': 'rsi_upper_limit',
        'atr_period': 'atr_period',
    }
    for param_key, attr_name in param_map.items():
        val = custom_params.get(param_key)
        if val is not None and hasattr(strategy, attr_name):
            setattr(strategy, attr_name, val)

    # SL/TP/Trailing
    if custom_params.get('sl_pct') is not None:
        strategy.backtest_sl_pct = custom_params['sl_pct']
    if custom_params.get('tp_pct') is not None:
        strategy.backtest_tp_pct = custom_params['tp_pct']
    if custom_params.get('trailing') is not None:
        strategy.use_trailing_stop = custom_params['trailing']
        if custom_params['trailing']:
            strategy.backtest_tp_pct = None

    # 필터 토글
    if custom_params.get('use_rsi_filter') is False:
        strategy.rsi_threshold = 0.0
        if hasattr(strategy, 'rsi_upper_limit'):
            strategy.rsi_upper_limit = 100.0
    if custom_params.get('use_adx_filter') is False:
        strategy.adx_threshold = 0.0
    if custom_params.get('use_volume_filter') is False:
        strategy.volume_multiplier = 0.0
    if custom_params.get('use_macd_filter') is False:
        if hasattr(strategy, 'macd_fast') and hasattr(strategy, 'macd_slow'):
            strategy.macd_fast = strategy.macd_slow


def get_strategy_with_custom_params(name: str, custom_params: dict | None = None):
    """커스텀 파라미터가 적용된 전략 인스턴스 반환"""
    strategy = get_strategy(name)
    if custom_params:
        apply_custom_params(strategy, custom_params)
    return strategy


# Alias for backward compatibility
MomentumBreakoutStrategy = MomentumBreakoutBasicStrategy
