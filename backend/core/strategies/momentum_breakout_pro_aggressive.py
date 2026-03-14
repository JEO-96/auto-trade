import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class MomentumBreakoutProAggressiveStrategy(BaseStrategy):
    """
    Momentum Breakout Pro (Aggressive) - Focuses on Profit Maximization
    - Softer filters to catch moves early
    - Wide trailing stop to capture full trends
    - Dynamic position sizing
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # Signal thresholds (aggressive - lower for faster entry)
        self.rsi_threshold = 55
        self.adx_threshold = 20
        self.volume_multiplier = 1.8

        # Exit parameters (wider stops, 1:4 risk-reward)
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 4.0
        self.trailing_stop_multiplier = 2.5

        # Pullback ADX threshold
        self.pullback_adx_threshold = 30

        # Risk scaling ADX threshold
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 2.0

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # Guard against NaN in critical indicator columns
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        if current['close'] < current['EMA_200']:
            return False

        # AGGRESSIVE criteria: Lower thresholds for faster entry
        breakout = (
            current[self.rsi_col] > self.rsi_threshold and
            current[self.adx_col] > self.adx_threshold and
            current[self.macd_col] > current[self.macds_col] and
            current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold and
                current['close'] > current['EMA_50'] and
                prev['close'] < prev_ema20 and
                current['close'] > current['EMA_20']
            )

        return breakout or pullback

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int) -> float:
        """Scale up risk in strong trends."""
        adx_val = df.iloc[current_idx].get(self.adx_col, 0)
        if pd.isna(adx_val):
            return 1.0
        if adx_val > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return 1.0
