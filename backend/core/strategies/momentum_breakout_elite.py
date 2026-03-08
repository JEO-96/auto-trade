import pandas as pd
import pandas_ta as ta
from core import config

class MomentumBreakoutEliteStrategy:
    """
    Momentum Breakout Elite (Hyper-Growth)
    - Optimized for Crypto Bull Markets (2020-2026+)
    - High-frequency trend capture
    - Dynamic risk-reward (1:4 to 1:6)
    - ATR-based trend trailing for maximum profit run
    """
    def __init__(self):
        self.use_trailing_stop = True

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df['VOL_SMA_20'] = df.ta.sma(close=df['volume'], length=20)
        
        # Trend filters
        df['EMA_200'] = df.ta.ema(length=200)
        df['EMA_100'] = df.ta.ema(length=100)
        df['EMA_50'] = df.ta.ema(length=50)
        df['EMA_20'] = df.ta.ema(length=20)
        
        # Volatility and Trend Strength
        df['ATR_14'] = df.ta.atr(length=14)
        adx_df = df.ta.adx(length=14)
        if adx_df is not None:
            df['ADX_14'] = adx_df['ADX_14']
            df['DMP_14'] = adx_df['DMP_14']
            df['DMN_14'] = adx_df['DMN_14']
        
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 100: return False
        
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_val = current.get('RSI_14', 50)
        adx_val = current.get('ADX_14', 0)
        dmp_val = current.get('DMP_14', 0)
        dmn_val = current.get('DMN_14', 0)
        macd_val = current.get('MACD_12_26_9', 0)
        macds_val = current.get('MACDs_12_26_9', 0)
        vol_avg = current['VOL_SMA_20']

        # 1. CORE BREAKOUT: Volume + RSI + MACD
        breakout = (
            rsi_val > 52 and 
            macd_val > macds_val and
            current['volume'] > vol_avg * 1.3 and
            current['close'] > current['EMA_100'] # Looser than 200 for earlier entry
        )

        # 2. TREND RIDER: Strong momentum regardless of volume spike
        trend_rider = (
            adx_val > 25 and
            dmp_val > dmn_val and
            current['close'] > current['EMA_20'] and
            prev['close'] < current['EMA_20'] and
            rsi_val > 50
        )

        # 3. PULLBACK ENTRY: Simple EMA touch in bull market
        bull_pullback = (
            current['close'] > current['EMA_200'] and
            prev['low'] < current['EMA_50'] and
            current['close'] > current['EMA_50'] and
            rsi_val > 45
        )

        return breakout or trend_rider or bull_pullback

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = df.iloc[entry_idx].get('ATR_14', entry_price * 0.02)
        # Tight Stop Loss for high Reward/Risk ratio
        stop_loss = entry_price - (atr * 1.5) 
        risk = entry_price - stop_loss
        
        # Ambitious Take Profit (1:5 ratio) for elite returns
        take_profit = entry_price + (risk * 5.0) 
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int):
        # Double the risk in extreme bull markets (ADX > 35)
        adx = df.iloc[current_idx].get('ADX_14', 0)
        if adx > 35:
            return 2.5 # Aggressive sizing in sure trends
        return 1.2 # Standard baseline risk slightly higher than basic

    def update_trailing_stop(self, current_price: float, current_atr: float, current_sl: float):
        # Very effective trailing stop for parabolic moves
        new_sl = current_price - (current_atr * 2.0)
        return max(current_sl, new_sl)
