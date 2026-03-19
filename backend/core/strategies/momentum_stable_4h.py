"""
MomentumStable4hStrategy - 4시간봉 최적화 모멘텀 안정형 전략

MaxDD 최소화 목표 (basic_4h 14.0% 이하 → 목표 <14%):
- RSI 임계값 53, RSI < 74 과매수 필터 (강화)
- ADX 임계값 22 (강화: 19→22)
- DI+ > DI- 방향성 필터 추가
- 볼륨 배수 1.5x
- ATR SL 1.2x, TP 2.5x, trailing 1.5x (타이트한 손절/익절)
- 골든크로스 필터 (EMA_50 > EMA_200)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable4hStrategy(BaseStrategy):
    """4시간봉 최적화 모멘텀 안정형 전략."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 4h 신호 임계값
        self.rsi_threshold = 53
        self.rsi_overbought = 76
        self.adx_threshold = 19
        self.volume_multiplier = 1.5

        # 4h 출구 파라미터
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.0

        # 백테스트 SL/TP (그리드 서치 최적화: 94% PnL, 34.3% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.25   # 25% TP

        # 풀백 ADX
        self.pullback_adx_threshold = 26

        # 위크 필터
        self.wick_filter_ratio = 0.9

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema50_gt_ema200 = True
        self.filter_rsi_max = 76

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 골든크로스 필터: EMA_50 > EMA_200
        if current['EMA_50'] <= current['EMA_200']:
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
