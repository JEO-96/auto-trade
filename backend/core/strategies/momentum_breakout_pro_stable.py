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

        # Exit parameters (tight stops, 1:2 risk-reward)
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 2.0
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

        adx_col = "ADX_14"

        # Guard against NaN in critical indicator columns
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, adx_col, 'EMA_200', 'EMA_20',
            'DMP_14', 'DMN_14',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 추세 필터: EMA_200 위 + ADX 방향 확인 (상승 추세만)
        if current['close'] < current['EMA_200']:
            return False
        if current['DMP_14'] <= current['DMN_14']:
            return False

        # RSI 과열 구간 진입 방지
        if current[self.rsi_col] > 80:
            return False

        # MACD 히스토그램 증가 확인
        macd_hist_col = f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
        hist_curr = current.get(macd_hist_col, None)
        hist_prev = prev.get(macd_hist_col, None)
        if hist_curr is not None and hist_prev is not None and not pd.isna(hist_curr) and not pd.isna(hist_prev):
            if hist_curr <= hist_prev:
                return False

        # STABLE criteria: Moderate-High thresholds (Version 2.0)
        breakout = (
            current[self.rsi_col] > self.rsi_threshold and
            current[adx_col] > self.adx_threshold and
            current[self.macd_col] > current[self.macds_col] and
            current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # Pullback only if strong enough
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[adx_col] > self.pullback_adx_threshold and
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
