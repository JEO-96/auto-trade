"""
TrendFollower15mStrategy - 15분봉 순수 추세추종 전략

순수 추세 추종 (새 컨셉):
- EMA_20 > EMA_50 > EMA_200 3중 정배열 필수
- DI+ > DI- + ADX 22+ (강한 추세만)
- RSI 50~72 밴드 (추세 유지 구간만)
- 가격이 EMA_20 위에서 반등할 때 진입
- 넓은 트레일링 스탑 2.5% (추세 최대 추종)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class TrendFollower15mStrategy(BaseStrategy):
    """
    15분봉 순수 추세추종 전략.

    3중 EMA 정배열 + DI 방향성으로 강한 상승 추세만 포착.
    넓은 트레일링 스탑으로 추세를 최대한 추종.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 출구 파라미터 (실매매용 ATR 기반)
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.5

        # 넓은 트레일링 스탑 (추세 최대 추종)
        self.backtest_sl_pct = 0.040   # 4.0% trailing stop
        self.backtest_tp_pct = None    # TP 없음
        self.backtest_trailing = True

        # 진입 조건
        self.adx_threshold = 22
        self.rsi_lower = 50
        self.rsi_upper = 72

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.adx_col,
            self.dmp_col, self.dmn_col,
            'EMA_200', 'EMA_50', 'EMA_20',
            self.macd_col, self.macds_col,
        ]
        if not self._validate_indicators(current, required_cols):
            return False

        # 3중 EMA 정배열: EMA_20 > EMA_50 > EMA_200
        if not (current['EMA_20'] > current['EMA_50'] > current['EMA_200']):
            return False

        # 가격 > EMA_20
        if current['close'] < current['EMA_20']:
            return False

        # DI+ > DI- (상승 추세)
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # ADX 강한 추세
        if current[self.adx_col] < self.adx_threshold:
            return False

        # RSI 추세 유지 밴드 (50~72)
        rsi = current[self.rsi_col]
        if rsi < self.rsi_lower or rsi > self.rsi_upper:
            return False

        # MACD > signal
        if current[self.macd_col] <= current[self.macds_col]:
            return False

        # 진입 트리거: 이전 봉이 EMA_20 근처에서 반등
        prev_ema20 = prev.get('EMA_20')
        if prev_ema20 is None or pd.isna(prev_ema20):
            return False

        # 이전 봉 저가가 EMA_20에 근접 (0.5% 이내) 또는 이전 봉 종가 < EMA_20
        ema20_proximity = abs(prev['low'] - prev_ema20) / prev_ema20 < 0.005
        prev_below_ema = prev['close'] < prev_ema20

        return ema20_proximity or prev_below_ema

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
