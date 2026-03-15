"""
MomentumStable1hStrategy - 1시간봉 최적화 모멘텀 안정형 전략

기본 momentum_breakout_pro_stable 대비 변경점:
- 볼륨 임계값 1.5x (1시간봉 노이즈 대응, 기존 2.1x)
- RSI 임계값 55 (기존 58), RSI < 75 과매수 필터 추가
- ADX 임계값 20 (기존 22)
- 위크 필터 완화 (0.9 ratio, 기존 0.8)
- 타이트한 ATR SL 1.3x, TP 2.5x, trailing 1.5x
"""
import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable1hStrategy(BaseStrategy):
    """
    1시간봉 최적화 모멘텀 안정형 전략.

    1시간봉은 노이즈가 많아 볼륨 필터를 완화하고,
    과매수 구간 진입을 방지하는 RSI 상한 가드를 추가.
    타이트한 손절/익절로 빠른 회전율 추구.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 신호 임계값 (1시간봉 완화)
        self.rsi_threshold = 55
        self.rsi_overbought = 75
        self.adx_threshold = 20
        self.volume_multiplier = 1.5

        # 출구 파라미터 (타이트한 손절/익절)
        self.atr_sl_multiplier = 1.3
        self.atr_tp_multiplier = 2.5
        self.trailing_stop_multiplier = 1.5

        # 풀백 ADX 임계값
        self.pullback_adx_threshold = 28

        # 위크 필터 (완화)
        self.wick_filter_ratio = 0.9

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_200', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # RSI 과매수 가드
        if current[self.rsi_col] > self.rsi_overbought:
            return False

        # 브레이크아웃 신호
        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # 풀백 신호
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
            )

        if breakout or pullback:
            # 위크 필터 (완화된 기준)
            body = abs(current['close'] - current['open'])
            wick = current['high'] - max(current['close'], current['open'])
            if body > 0 and wick > body * self.wick_filter_ratio:
                return False
            return True

        return False

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
