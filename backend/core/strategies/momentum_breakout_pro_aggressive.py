import pandas as pd
import pandas_ta as ta
from core import config

class MomentumBreakoutProAggressiveStrategy:
    """
    Momentum Breakout Pro (Aggressive) - Focuses on Profit Maximization
    - Softer filters to catch moves early
    - Wide trailing stop to capture full trends
    - Dynamic position sizing
    """
    def __init__(self):
        self.use_trailing_stop = True

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df.ta.rsi(length=config.RSI_PERIOD, append=True)
        df.ta.macd(fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL, append=True)
        df[f'VOL_SMA_{config.VOLUME_MA_PERIOD}'] = df.ta.sma(close=df['volume'], length=config.VOLUME_MA_PERIOD)
        
        df['EMA_200'] = df.ta.ema(length=200)
        df['EMA_50'] = df.ta.ema(length=50)
        df['EMA_20'] = df.ta.ema(length=20)
        
        atr_df = df.ta.atr(length=14)
        if atr_df is not None:
            df['ATR_14'] = atr_df
            
        adx_df = df.ta.adx(length=14)
        if adx_df is not None:
            df['ADX_14'] = adx_df['ADX_14']
            df['DMP_14'] = adx_df['DMP_14']
            df['DMN_14'] = adx_df['DMN_14']
        
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200: return False
        
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_col = f"RSI_{config.RSI_PERIOD}"
        macd_col = f"MACD_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"
        macds_col = f"MACDs_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"
        vol_ma_col = f"VOL_SMA_{config.VOLUME_MA_PERIOD}"
        adx_col = "ADX_14"

        if current['close'] < current['EMA_200']: return False

        # AGGRESSIVE criteria: Lower thresholds for faster entry
        breakout = (
            current[rsi_col] > 55 and 
            current[adx_col] > 20 and 
            current[macd_col] > current[macds_col] and
            current['volume'] > current[vol_ma_col] * 1.8
        )
        
        pullback = (
            current[adx_col] > 30 and
            current['close'] > current['EMA_50'] and
            prev['close'] < prev['EMA_20'] and
            current['close'] > current['EMA_20']
        )

        return breakout or pullback

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = df.iloc[entry_idx]['ATR_14']
        stop_loss = entry_price - (atr * 2.0)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * 4.0) 
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int):
        # Scale up risk in strong trends
        if df.iloc[current_idx]['ADX_14'] > 35:
            return 2.0
        return 1.0

    def update_trailing_stop(self, current_price: float, current_atr: float, current_sl: float):
        new_sl = current_price - (current_atr * 2.5) # Wide trailing to capture mega moves
        return max(current_sl, new_sl)
