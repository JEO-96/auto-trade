import pandas_ta as ta
import pandas as pd
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

        rsi_cross_up = (prev[rsi_col] <= config.RSI_OVERBOUGHT) and (current[rsi_col] > config.RSI_OVERBOUGHT)
        macd_positive = current[macd_col] > current[macds_col]
        vol_ma_col = f"VOL_SMA_{config.VOLUME_MA_PERIOD}"
        volume_spike = current['volume'] > (current[vol_ma_col] * config.VOLUME_SPIKE_MULTIPLIER)

        if (current[rsi_col] > config.RSI_OVERBOUGHT) and macd_positive and volume_spike:
            if rsi_cross_up or (current[rsi_col] - prev[rsi_col] > 5):
                return True
        return False

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        prev_low = df.iloc[entry_idx - 1]['low']
        curr_low = df.iloc[entry_idx]['low']
        stop_loss = min(prev_low, curr_low)
        if entry_price <= stop_loss or (entry_price - stop_loss) / entry_price < 0.005:
            stop_loss = entry_price * 0.985
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * config.RISK_REWARD_RATIO)
        return stop_loss, take_profit
