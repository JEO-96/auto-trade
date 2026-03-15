"""
MomentumAggressive1hStrategy - 1시간봉 전용 공격적 모멘텀 전략.

공격형 전략답게 진입 기회를 넓히고 큰 수익을 노림:
- RSI 55 (낮은 임계값으로 더 많은 진입 기회)
- ADX 20 (추세 초기 단계에서 진입)
- 볼륨 1.5x (1h 볼륨 노이즈 보정)
- EMA_200 매크로 필터만 사용 (EMA_20/50 정렬 제거 — 더 공격적)
- ATR SL 1.5x, TP 4.0x (1:4 RR), trailing 2.5x (큰 수익 추구)
- 리스크 스케일링: ADX > 35일 때 2.0x (공격적 포지션 확대)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumAggressive1hStrategy(BaseStrategy):
    """
    1시간봉 전용 공격적 모멘텀 브레이크아웃 전략.

    Basic 대비 공격적 변경점:
    - 낮은 RSI/ADX 임계값으로 더 많은 진입 기회
    - EMA_20 > EMA_50 정렬 조건 제거 (진입 제약 완화)
    - 높은 TP 배수(4.0x)로 큰 수익 추구
    - 넓은 trailing stop(2.5x)으로 수익 극대화
    - 높은 리스크 스케일링 (2.0x)
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 공격적 신호 임계값 (낮은 진입 장벽)
        self.rsi_threshold = 55
        self.adx_threshold = 20
        self.volume_multiplier = 1.5

        # 공격적 출구 파라미터 (큰 수익 추구, 1:4 RR)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 4.0
        self.trailing_stop_multiplier = 2.5

        # 백테스트 SL/TP (그리드 서치 최적화: 125% PnL, 37.1% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.15   # 15% TP

        # 풀백 ADX 임계값 (더 많은 풀백 진입)
        self.pullback_adx_threshold = 25

        # 리스크 스케일링 (공격적)
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 2.0

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

        # 매크로 추세 필터: 가격 > EMA_200 (유일한 EMA 필터)
        if current['close'] < current['EMA_200']:
            return False

        # EMA_20 > EMA_50 정렬 필터 제거 — 공격적 전략은 진입 제약 최소화

        # 브레이크아웃 조건 (공격적: 낮은 임계값으로 진입 기회 확대)
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
        """공격적 리스크 스케일링: ADX > 35일 때 2.0x 포지션 확대."""
        adx_val = df.iloc[current_idx].get(self.adx_col, 0)
        if pd.isna(adx_val):
            return 1.0
        if adx_val > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return 1.0
