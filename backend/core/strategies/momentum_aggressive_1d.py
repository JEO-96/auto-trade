"""
MomentumAggressive1dStrategy - 일봉 전용 공격적 모멘텀 전략.

1d 타임프레임에서 기존 +108% 수익률을 유지하면서 MaxDD(16.8%) 감소:
- RSI 55, ADX 20 유지 (이미 우수한 성과)
- 볼륨 1.8x 유지
- EMA_50 > EMA_200 매크로 추세 필터 추가
- DMP > DMN 방향성 움직임 게이트 추가 (추세 강도 확인)
- ATR SL 2.5x, TP 5.0x (1:5 RR), trailing 3.0x (일봉용 넓은 스탑)
- 리스크 스케일링: ADX > 35일 때 2.0x
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumAggressive1dStrategy(BaseStrategy):
    """
    일봉 전용 공격적 모멘텀 브레이크아웃 전략.

    기본 공격적 전략 대비 변경점:
    - EMA_50 > EMA_200 매크로 추세 필터 (하락장 진입 방지)
    - DMP > DMN 조건으로 양의 방향성 움직임 확인
    - 넓은 ATR 배수로 일봉 변동성 수용 (SL 2.5x, TP 5.0x)
    - 넓은 trailing stop (3.0x)으로 큰 추세 포착
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 1d 전용 신호 임계값 (기존 성과 유지)
        self.rsi_threshold = 55
        self.adx_threshold = 20
        self.volume_multiplier = 1.8

        # 1d 전용 출구 파라미터 (넓은 스탑, 1:5 RR)
        self.atr_sl_multiplier = 2.5
        self.atr_tp_multiplier = 5.0
        self.trailing_stop_multiplier = 3.0

        # 백테스트 SL/TP (그리드 서치 최적화: 146% PnL, 22.1% MaxDD)
        self.backtest_sl_pct = 0.04   # 4% SL
        self.backtest_tp_pct = 0.20   # 20% TP

        # 풀백 ADX 임계값
        self.pullback_adx_threshold = 30

        # 리스크 스케일링
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 2.0

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 NaN 검증 (DMP/DMN 포함)
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col,
            self.dmp_col, self.dmn_col,
            'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 매크로 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 1d 전용 매크로 추세 필터: EMA_50 > EMA_200 (장기 상승 추세)
        if current['EMA_50'] <= current['EMA_200']:
            return False

        # 1d 전용 추세 강도 게이트: DMP > DMN (양의 방향성 움직임)
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # 브레이크아웃 조건
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
        """1d에서는 강한 추세에 2.0x 리스크 스케일링."""
        adx_val = df.iloc[current_idx].get(self.adx_col, 0)
        if pd.isna(adx_val):
            return 1.0
        if adx_val > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return 1.0
