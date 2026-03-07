import pandas_ta as ta
import pandas as pd
import config

class MomentumBreakoutStrategy:
    def __init__(self):
        pass

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates required indicators: RSI, MACD, and Volume MA.
        """
        # 1. Calculate RSI
        df.ta.rsi(length=config.RSI_PERIOD, append=True)

        # 2. Calculate MACD
        df.ta.macd(fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL, append=True)

        # 3. Calculate Volume Moving Average
        df[f'VOL_SMA_{config.VOLUME_MA_PERIOD}'] = df.ta.sma(close=df['volume'], length=config.VOLUME_MA_PERIOD)

        # Rename columns for easier access (pandas_ta appends with specific names)
        # RSI column is usually something like 'RSI_14'
        rsi_col = f"RSI_{config.RSI_PERIOD}"
        macd_col = f"MACD_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"
        macds_col = f"MACDs_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}" # Signal line
        macdh_col = f"MACDh_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}" # Histogram

        # Ensure we have the columns
        if not all(col in df.columns for col in [rsi_col, macd_col, macds_col]):
            print("Failed to calculate indicators properly.")
            return df

        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        """
        Checks if the James Momentum Breakout conditions are met at a specific index.
        Conditions:
        int: Index to check
        1. RSI 60 Cross Up
        2. MACD Golden Cross (MACD > Signal)
        3. Volume > 200% of Volume MA
        """
        if current_idx < 1:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_col = f"RSI_{config.RSI_PERIOD}"
        macd_col = f"MACD_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"
        macds_col = f"MACDs_{config.MACD_FAST}_{config.MACD_SLOW}_{config.MACD_SIGNAL}"

        # 1. RSI > 60 Cross Up (Previous RSI <= 60 and Current RSI > 60)
        rsi_cross_up = (prev[rsi_col] <= config.RSI_OVERBOUGHT) and (current[rsi_col] > config.RSI_OVERBOUGHT)
        
        # Alternatively, sometimes momentum is just defined as RSI > 60 strongly rising. 
        # For a strict breakout, we check the cross-up or simply RSI > 60. Let's use strict cross-up.
        
        # 2. MACD Golden Cross OR MACD > Signal showing positive momentum
        # Let's define it as MACD is currently above Signal and Histogram is positive
        macd_positive = current[macd_col] > current[macds_col]
        
        # 3. Volume > 200% MA
        vol_ma_col = f"VOL_SMA_{config.VOLUME_MA_PERIOD}"
        volume_spike = current['volume'] > (current[vol_ma_col] * config.VOLUME_SPIKE_MULTIPLIER)

        # James Momentum Breakout specific combination:
        # We look for RSI bursting through 60, MACD confirming upward trend, and a massive volume spike.
        if (current[rsi_col] > config.RSI_OVERBOUGHT) and macd_positive and volume_spike:
            # Check if this is truly the breakout candle (RSI just crossed or is accelerating)
            if rsi_cross_up or (current[rsi_col] - prev[rsi_col] > 5): # Sharp rise
                return True
                
        return False

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        """
        Calculates Stop Loss and Take Profit levels based on the swing low and risk-reward ratio.
        """
        # Stop loss: the low of the entry candle or previous candle, whichever is lower
        prev_low = df.iloc[entry_idx - 1]['low']
        curr_low = df.iloc[entry_idx]['low']
        stop_loss = min(prev_low, curr_low)
        
        # If the stop loss is too tight or equal to entry, impose a minimum e.g., 1%
        if entry_price <= stop_loss or (entry_price - stop_loss) / entry_price < 0.005:
            stop_loss = entry_price * 0.985 # Default 1.5% SL
            
        risk = entry_price - stop_loss
        
        # Take Profit: Risk x Reward Ratio
        take_profit = entry_price + (risk * config.RISK_REWARD_RATIO)
        
        return stop_loss, take_profit
