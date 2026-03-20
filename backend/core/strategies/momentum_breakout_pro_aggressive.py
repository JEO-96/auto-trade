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

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True

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

    def get_trigger_signals(
        self, df: pd.DataFrame, current_idx: int, curr_price: float
    ) -> list[tuple[str, bool]]:
        if current_idx < 1:
            return []

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        def _val(row, col):
            v = row.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            return v

        triggers: list[tuple[str, bool]] = []

        # 신호 1: 브레이크아웃
        rsi = _val(current, self.rsi_col)
        adx = _val(current, self.adx_col)
        macd = _val(current, self.macd_col)
        macds = _val(current, self.macds_col)
        vol = _val(current, 'volume')
        vol_ma = _val(current, self.vol_ma_col)
        if all(v is not None for v in (rsi, adx, macd, macds, vol, vol_ma)) and vol_ma > 0:
            is_met = (
                rsi > self.rsi_threshold
                and adx > self.adx_threshold
                and macd > macds
                and vol > vol_ma * self.volume_multiplier
            )
            triggers.append(("브레이크아웃 (RSI/ADX/MACD/볼륨)", bool(is_met)))

        # 신호 2: 풀백 진입
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        ema50 = _val(current, 'EMA_50')
        prev_close = _val(prev, 'close')
        if all(v is not None for v in (adx, ema50, prev_ema20, prev_close, curr_ema20)):
            is_met = (
                adx > self.pullback_adx_threshold
                and curr_price > ema50
                and prev_close < prev_ema20
                and curr_price > curr_ema20
            )
            triggers.append(("풀백 진입 (ADX/EMA50/EMA20 반등)", bool(is_met)))

        return triggers

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
