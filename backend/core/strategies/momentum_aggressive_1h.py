"""
MomentumAggressive1hStrategy - 1시간봉 전용 공격적 모멘텀 전략.

1h 타임프레임의 노이즈를 줄이기 위해 더 엄격한 진입 필터 적용:
- RSI 58 (높은 임계값으로 가짜 신호 감소)
- ADX 24 (확인된 추세만 진입)
- 볼륨 1.5x (1h 볼륨 노이즈 보정)
- EMA 정렬 필터: EMA_20 > EMA_50 (단기 상승 추세 확인)
- ATR SL 1.5x, TP 3.0x (1:3 RR), trailing 2.0x
- 리스크 스케일링: ADX > 35일 때 1.5x (보수적)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumAggressive1hStrategy(BaseStrategy):
    """
    1시간봉 전용 공격적 모멘텀 브레이크아웃 전략.

    기본 공격적 전략 대비 변경점:
    - 더 높은 RSI/ADX 임계값으로 선별적 진입
    - EMA_20 > EMA_50 정렬 조건 추가
    - 타이트한 ATR 배수로 1h 변동성 대응
    - 낮은 리스크 스케일링 (1.5x)
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 1h 전용 신호 임계값 (더 엄격)
        self.rsi_threshold = 58
        self.adx_threshold = 24
        self.volume_multiplier = 1.5

        # 1h 전용 출구 파라미터 (타이트, 1:3 RR)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 3.0
        self.trailing_stop_multiplier = 2.0

        # 풀백 ADX 임계값
        self.pullback_adx_threshold = 30

        # 리스크 스케일링 (보수적)
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 1.5

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 NaN 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col,
            'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 매크로 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 1h 전용 EMA 정렬 필터: EMA_20 > EMA_50 (단기 상승 추세)
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 브레이크아웃 조건 (1h 전용: 더 높은 임계값)
        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # 풀백 진입 조건
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and current['close'] > current['EMA_50']
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
            )

        return breakout or pullback

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int) -> float:
        """1h에서는 보수적 리스크 스케일링 (1.5x)."""
        adx_val = df.iloc[current_idx].get(self.adx_col, 0)
        if pd.isna(adx_val):
            return 1.0
        if adx_val > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return 1.0
