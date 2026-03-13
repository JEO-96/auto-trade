import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class MomentumBreakoutEliteStrategy(BaseStrategy):
    """
    Momentum Breakout Elite (Hyper-Growth)
    - Optimized for Crypto Bull Markets (2020-2026+)
    - High-frequency trend capture
    - Dynamic risk-reward (1:4 to 1:6)
    - ATR-based trend trailing for maximum profit run
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # Elite uses hardcoded indicator params (not config)
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.volume_ma_period = 20

        # Signal thresholds (loose for maximum entries)
        self.rsi_threshold = 52
        self.adx_threshold = 25
        self.volume_multiplier = 1.3

        # Exit parameters (tight SL, very ambitious TP - 1:5)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 5.0
        self.trailing_stop_multiplier = 2.0

        # Trend rider parameters
        self.trend_rider_rsi_min = 50
        self.trend_rider_adx_min = 25

        # Bull pullback RSI threshold
        self.pullback_rsi_min = 45

        # Risk scaling
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 2.5
        self.risk_default_multiplier = 1.2

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Elite adds EMA_100 on top of the standard indicator set."""
        df = super().apply_indicators(df)
        ema100 = df.ta.ema(length=100)
        df['EMA_100'] = ema100.iloc[:, 0] if hasattr(ema100, 'iloc') and ema100.ndim > 1 else ema100
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_val = current.get(self.rsi_col, None)
        adx_val = current.get('ADX_14', None)
        dmp_val = current.get('DMP_14', None)
        dmn_val = current.get('DMN_14', None)
        macd_val = current.get(self.macd_col, None)
        macds_val = current.get(self.macds_col, None)
        vol_avg = current.get(self.vol_ma_col, None)
        ema_200 = current.get('EMA_200', None)
        ema_100 = current.get('EMA_100', None)
        ema_50 = current.get('EMA_50', None)
        ema_20 = current.get('EMA_20', None)

        # Guard against NaN -- any NaN in core indicators means skip
        core_vals = [rsi_val, macd_val, macds_val, vol_avg, ema_100, ema_20]
        if any(v is None or pd.isna(v) for v in core_vals):
            return False
        if vol_avg == 0:
            return False

        # 1. CORE BREAKOUT: Volume + RSI + MACD
        breakout = (
            rsi_val > self.rsi_threshold and
            macd_val > macds_val and
            current['volume'] > vol_avg * self.volume_multiplier and
            current['close'] > ema_100
        )

        # 2. TREND RIDER: Strong momentum regardless of volume spike
        #    Needs ADX/DMP/DMN to be valid
        trend_rider = False
        if not any(v is None or pd.isna(v) for v in [adx_val, dmp_val, dmn_val]):
            prev_ema20 = prev.get('EMA_20', None)
            if prev_ema20 is not None and not pd.isna(prev_ema20):
                trend_rider = (
                    adx_val > self.trend_rider_adx_min and
                    dmp_val > dmn_val and
                    current['close'] > ema_20 and
                    prev['close'] < prev_ema20 and
                    rsi_val > self.trend_rider_rsi_min
                )

        # 3. PULLBACK ENTRY: Simple EMA touch in bull market
        bull_pullback = False
        if ema_200 is not None and not pd.isna(ema_200) and ema_50 is not None and not pd.isna(ema_50):
            bull_pullback = (
                current['close'] > ema_200 and
                prev['low'] < ema_50 and
                current['close'] > ema_50 and
                rsi_val > self.pullback_rsi_min
            )

        return breakout or trend_rider or bull_pullback

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        # Tight Stop Loss for high Reward/Risk ratio
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        # Ambitious Take Profit (1:5 ratio) for elite returns
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int) -> float:
        """Double the risk in extreme bull markets (ADX > 35)."""
        adx = df.iloc[current_idx].get('ADX_14', 0)
        if adx is None or pd.isna(adx):
            return 1.0
        if adx > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return self.risk_default_multiplier
