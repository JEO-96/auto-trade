import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class MomentumBreakoutProStableStrategy(BaseStrategy):
    """
    Momentum Breakout Pro (Stable) - Focuses on Capital Preservation
    - Strict filters to avoid fakes
    - Tight trailing stop
    - Defensive sizing
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # Signal thresholds (conservative)
        self.rsi_threshold = 58
        self.adx_threshold = 22
        self.volume_multiplier = 2.1

        # Exit parameters (tight stops, 1:3 risk-reward)
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 3.0
        self.trailing_stop_multiplier = 1.8

        # Pullback ADX threshold
        self.pullback_adx_threshold = 30

        # Wick filter ratio
        self.wick_filter_ratio = 0.8

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # Guard against NaN in critical indicator columns
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_200', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # trend check
        if current['close'] < current['EMA_200']:
            return False

        # STABLE criteria: Moderate-High thresholds (Version 2.0)
        breakout = (
            current[self.rsi_col] > self.rsi_threshold and
            current[self.adx_col] > self.adx_threshold and
            current[self.macd_col] > current[self.macds_col] and
            current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # Pullback only if strong enough
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold and
                prev['close'] < prev_ema20 and
                current['close'] > current['EMA_20']
            )

        if breakout or pullback:
            # Wick filter for safety
            body = abs(current['close'] - current['open'])
            wick = current['high'] - max(current['close'], current['open'])
            if body > 0 and wick > body * self.wick_filter_ratio:
                return False
            return True
        return False

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
