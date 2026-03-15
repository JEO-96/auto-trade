"""
MomentumAggressive4hStrategy - 4시간봉 전용 공격적 모멘텀 전략.

4h 타임프레임의 가짜 진입을 줄이기 위한 최적화:
- RSI 56, ADX 22 (중간 수준 필터)
- 볼륨 1.6x (4h 볼륨 특성 반영)
- MACD 히스토그램 > 0 AND 증가 조건 추가 (단순 MACD > signal 대신)
- 풀백 ADX 28 (더 선별적)
- ATR SL 1.8x, TP 3.5x (1:3.5 RR), trailing 2.2x
- 리스크 스케일링: ADX > 35일 때 1.8x
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumAggressive4hStrategy(BaseStrategy):
    """
    4시간봉 전용 공격적 모멘텀 브레이크아웃 전략.

    기본 공격적 전략 대비 변경점:
    - MACD 히스토그램 증가 조건으로 모멘텀 확인
    - 중간 수준 RSI/ADX 필터
    - 풀백 ADX 28로 가짜 풀백 진입 감소
    - 1.8x 리스크 스케일링
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 4h 전용 신호 임계값
        self.rsi_threshold = 56
        self.adx_threshold = 22
        self.volume_multiplier = 1.6

        # 4h 전용 출구 파라미터 (1:3.5 RR)
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.2

        # 백테스트 SL/TP (그리드 서치 최적화: 214% PnL, 17.9% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.08   # 8% TP

        # 풀백 ADX 임계값 (더 선별적)
        self.pullback_adx_threshold = 28

        # 리스크 스케일링
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 1.8

    @property
    def macdh_col(self) -> str:
        """MACD 히스토그램 컬럼명."""
        return f"MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 NaN 검증 (히스토그램 포함)
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col, self.macdh_col,
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

        # 이전 봉 히스토그램 NaN 검증
        prev_macdh = prev.get(self.macdh_col)
        if prev_macdh is None or pd.isna(prev_macdh):
            prev_macdh_valid = False
        else:
            prev_macdh_valid = True

        # 브레이크아웃 조건 (4h 전용: MACD 히스토그램 > 0 AND 증가)
        macd_histogram_positive = current[self.macdh_col] > 0
        macd_histogram_increasing = (
            prev_macdh_valid
            and current[self.macdh_col] > prev_macdh
        )

        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and macd_histogram_positive
            and macd_histogram_increasing
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # 풀백 진입 조건 (더 높은 ADX 요구)
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
        """4h에서는 중간 리스크 스케일링 (1.8x)."""
        adx_val = df.iloc[current_idx].get(self.adx_col, 0)
        if pd.isna(adx_val):
            return 1.0
        if adx_val > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return 1.0
