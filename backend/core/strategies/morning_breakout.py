import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MorningBreakoutStrategy(BaseStrategy):
    """
    Morning Breakout Strategy V1 (Larry Williams' Volatility Breakout).
    
    Target: 9:00 AM KST daily candlestick.
    Buy Signal: Current Price > Today's Open + (Yesterday's Range * K). Default K = 0.5.
    Exit Signal: 
        1. Next day 9:00 AM (Time-based exit) -> Handled by BOT logic or check_sell_signal.
        2. Stop Loss 2%.
    """

    def __init__(self, k: float = 0.5):
        super().__init__()
        self.k = k
        self.backtest_sl_pct = 0.02
        self.backtest_tp_pct = None  # Time-based exit at next 9 AM
        
        # UI/Notification flags
        self.filter_volume_min = 1.0

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates indicators needed for Morning Breakout.
        Expects 1D interval data or appropriately sampled data.
        """
        # Yesterday's Range = High - Low
        df['prev_high'] = df['high'].shift(1)
        df['prev_low'] = df['low'].shift(1)
        df['prev_range'] = df['prev_high'] - df['prev_low']
        
        # Target Price = Open + (Range * K)
        df['target_price'] = df['open'] + (df['prev_range'] * self.k)
        
        # Standard indicators for meta-data/filtering
        df = super().apply_indicators(df)
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        """
        Entry: Current price > Target price.
        """
        if current_idx < 1:
            return False

        current = df.iloc[current_idx]
        
        target_price = current.get('target_price')
        curr_price = current['close']
        
        if pd.isna(target_price) or target_price <= 0:
            return False
            
        # Volatility breakout trigger
        if curr_price > target_price:
            return True
            
        return False

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        """
        Fixed SL at 2%. 
        TP is None because we use time-based exit (next day open).
        """
        stop_loss = entry_price * (1 - self.backtest_sl_pct)
        take_profit = None 
        return stop_loss, take_profit

    def get_trigger_signals(self, df: pd.DataFrame, current_idx: int, curr_price: float) -> list[tuple[str, bool]]:
        current = df.iloc[current_idx]
        target = current.get('target_price', 0)
        return [
            (f"변동성 돌파 (>{target:,.0f})", curr_price > target)
        ]
