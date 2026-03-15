"""
MomentumBasic1D - 일봉 최적화 모멘텀 브레이크아웃 전략

기본 전략(momentum_breakout_basic) 대비 개선 사항:
- EMA_200 + EMA_50 이중 트렌드 필터 (강한 추세 정렬만 진입)
- RSI 임계값 62 (일봉은 강한 신호만 유효)
- 볼륨 배수 2.0x (일봉 거래량은 안정적이므로 기본값 유지)
- ADX > 25 필터 (강한 추세에서만 진입)
- ATR 기반 손절/익절 (SL 2.0x, TP 4.0x RR) — 일봉 변동성 반영
- 트레일링 스탑 2.5x ATR
- 풀백 진입 조건 추가 (MaxDD 감소 목적)
- DI+ > DI- 방향성 필터 (추세 방향 확인)

백테스트 기준선: +52.04% / 70거래 / 52.9% 승률 / 42.2% MaxDD
목표: MaxDD 대폭 감소 (42% → 25% 이하) + 승률 유지/향상
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumBasic1DStrategy(BaseStrategy):
    """
    일봉 최적화 모멘텀 브레이크아웃.

    일봉은 신호 하나당 영향이 크므로 엄격한 필터가 필수.
    EMA_200 + EMA_50 이중 트렌드 정렬로 장기 하락장 진입을 완전 차단.
    ADX 25 이상 + DI+ > DI- 조건으로 강한 상승 추세에서만 진입.
    풀백 진입(EMA_20 반등)을 추가하여 추세 지속 구간에서
    더 좋은 가격에 진입하고 MaxDD를 줄임.
    넓은 ATR 기반 SL/TP로 일봉 변동성을 수용.
    """

    def __init__(self) -> None:
        super().__init__()
        self.use_trailing_stop = True

        # 일봉 최적화 신호 임계값 (엄격)
        self.rsi_threshold = 62.0
        self.adx_threshold = 25.0
        self.volume_multiplier = 2.0

        # 일봉 최적화 출구 파라미터 (넓은 SL/TP)
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 4.0
        self.trailing_stop_multiplier = 2.5

        # 풀백 진입용 ADX 임계값
        self.pullback_adx_threshold = 30

        # 윅 필터 비율
        self.wick_filter_ratio = 0.9

        # RSI 과열 상한 (일봉에서 과매수 구간 진입 방지)
        self.rsi_upper_limit = 78.0

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        # EMA_200 계산에 충분한 데이터 필요
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 NaN 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, self.dmp_col, self.dmn_col,
            'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # --- 이중 트렌드 필터: 가격 > EMA_200 AND EMA_50 > EMA_200 ---
        if current['close'] < current['EMA_200']:
            return False
        if current['EMA_50'] < current['EMA_200']:
            return False

        # --- 방향성 필터: DI+ > DI- (상승 추세 확인) ---
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # --- RSI 과열 방지 (과매수 구간 진입 거부) ---
        rsi_curr = current[self.rsi_col]
        if rsi_curr > self.rsi_upper_limit:
            return False

        rsi_prev = prev.get(self.rsi_col)
        if rsi_prev is None or pd.isna(rsi_prev):
            return False

        # --- 신호 1: 모멘텀 브레이크아웃 ---
        rsi_cross_up = (rsi_prev <= self.rsi_threshold) and (rsi_curr > self.rsi_threshold)
        rsi_momentum = rsi_curr - rsi_prev > 5

        breakout = (
            (rsi_cross_up or (rsi_curr > self.rsi_threshold and rsi_momentum))
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # --- 신호 2: 풀백 진입 (EMA_20 반등, 강한 추세에서만) ---
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
                and current[self.macd_col] > current[self.macds_col]
                and current['volume'] > current[self.vol_ma_col]  # 최소 평균 이상 거래량
            )

        if not (breakout or pullback):
            return False

        # --- 윅 필터 (과도한 상단 꼬리 거부, 일봉은 관대하게) ---
        body = abs(current['close'] - current['open'])
        wick = current['high'] - max(current['close'], current['open'])
        if body > 0 and wick > body * self.wick_filter_ratio:
            return False

        return True

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
