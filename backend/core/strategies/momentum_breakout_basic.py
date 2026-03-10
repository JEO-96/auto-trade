import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class MomentumBreakoutBasicStrategy(BaseStrategy):
    """
    Basic momentum breakout strategy.
    Uses RSI cross-up, MACD positivity, and volume spike for entry.
    Exit levels are based on recent candle lows + risk-reward ratio.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = False

        # Basic strategy uses config-level thresholds
        self.rsi_threshold = config.RSI_OVERBOUGHT
        self.volume_multiplier = config.VOLUME_SPIKE_MULTIPLIER

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Basic strategy only needs RSI, MACD, and Volume SMA (no EMAs/ATR/ADX)."""
        df.ta.rsi(length=self.rsi_period, append=True)
        df.ta.macd(
            fast=self.macd_fast,
            slow=self.macd_slow,
            signal=self.macd_signal,
            append=True,
        )
        df[self.vol_ma_col] = df.ta.sma(
            close=df['volume'], length=self.volume_ma_period
        )
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 1:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_curr = current.get(self.rsi_col)
        rsi_prev = prev.get(self.rsi_col)
        macd_curr = current.get(self.macd_col)
        macds_curr = current.get(self.macds_col)
        vol_ma_curr = current.get(self.vol_ma_col)

        if any(pd.isna(v) for v in [rsi_curr, rsi_prev, macd_curr, macds_curr, vol_ma_curr]):
            return False
        if vol_ma_curr == 0:
            return False

        # RSI 과열 구간 진입 방지 (RSI > 80이면 고점 추격 회피)
        if rsi_curr > 80:
            return False

        rsi_cross_up = (rsi_prev <= config.RSI_OVERBOUGHT) and (rsi_curr > config.RSI_OVERBOUGHT)
        macd_positive = macd_curr > macds_curr
        volume_spike = current['volume'] > (vol_ma_curr * self.volume_multiplier)

        # MACD 히스토그램 증가 확인 (모멘텀 가속 중인지)
        macd_hist_col = f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"
        hist_curr = current.get(macd_hist_col, None)
        hist_prev = prev.get(macd_hist_col, None)
        if hist_curr is not None and hist_prev is not None and not pd.isna(hist_curr) and not pd.isna(hist_prev):
            if hist_curr <= hist_prev:
                return False  # 모멘텀 감속 중이면 진입 안 함

        if (rsi_curr > config.RSI_OVERBOUGHT) and macd_positive and volume_spike:
            if rsi_cross_up:
                return True
        return False

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        if entry_price <= 0:
            return entry_price * 0.985, entry_price * 1.015

        if entry_idx >= 1:
            prev_low = df.iloc[entry_idx - 1]['low']
            curr_low = df.iloc[entry_idx]['low']
            stop_loss = min(prev_low, curr_low)
        else:
            stop_loss = entry_price * 0.985

        if entry_price <= stop_loss or (entry_price - stop_loss) / entry_price < 0.005:
            stop_loss = entry_price * 0.985

        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * config.RISK_REWARD_RATIO)
        return stop_loss, take_profit
