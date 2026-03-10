import pandas_ta as ta
import pandas as pd
import numpy as np
from core import config

class MomentumBreakoutBasicStrategy:
    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df.ta.rsi(length=config.RSI_PERIOD, append=True)
        df.ta.macd(fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL, append=True)
        df[f'VOL_SMA_{config.VOLUME_MA_PERIOD}'] = df.ta.sma(close=df['volume'], length=config.VOLUME_MA_PERIOD)
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 1: return False
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_col = f"RSI_{config.RSI_PERIOD}"
        macd_col = f"MACD_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"
        macds_col = f"MACDs_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"

        # Guard against NaN values in indicator columns
        rsi_curr = current.get(rsi_col)
        rsi_prev = prev.get(rsi_col)
        macd_curr = current.get(macd_col)
        macds_curr = current.get(macds_col)
        vol_ma_col = f"VOL_SMA_{config.VOLUME_MA_PERIOD}"
        vol_ma_curr = current.get(vol_ma_col)

        if any(pd.isna(v) for v in [rsi_curr, rsi_prev, macd_curr, macds_curr, vol_ma_curr]):
            return False
        if vol_ma_curr == 0:
            return False

        rsi_cross_up = (rsi_prev <= config.RSI_OVERBOUGHT) and (rsi_curr > config.RSI_OVERBOUGHT)
        macd_positive = macd_curr > macds_curr
        volume_spike = current['volume'] > (vol_ma_curr * config.VOLUME_SPIKE_MULTIPLIER)

        if (rsi_curr > config.RSI_OVERBOUGHT) and macd_positive and volume_spike:
            if rsi_cross_up or (rsi_curr - rsi_prev > 5):
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
            # Not enough history to look back; use a percentage-based fallback
            stop_loss = entry_price * 0.985

        if entry_price <= stop_loss or (entry_price - stop_loss) / entry_price < 0.005:
            stop_loss = entry_price * 0.985

        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * config.RISK_REWARD_RATIO)
        return stop_loss, take_profit
