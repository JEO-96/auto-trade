"""
MomentumStable1dStrategy - 일봉 최적화 모멘텀 안정형 전략

기본 momentum_breakout_pro_stable 대비 대폭 수정:
- 볼륨 임계값 1.5x (일봉 변동폭 대응, 기존 2.1x)
- RSI 임계값 52 (초기 움직임 포착, 기존 58)
- ADX 임계값 18 (일봉 추세 형성이 느림, 기존 22)
- 넓은 ATR SL 2.5x, TP 5.0x, trailing 3.0x
- EMA_50 > EMA_200 골든크로스 필터 (강한 상승 추세만)
- 최근 5봉 최고 종가 돌파 조건 추가
- 위크 필터 제거 (일봉 캔들은 몸통이 길어 의미 없음)

기존 일봉 결과: -37.61% (65거래, 33.8% 승률, 44.6% MaxDD)
개선 목표: 강한 추세 구간만 선별 진입하여 승률/수익률 개선
"""
import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable1dStrategy(BaseStrategy):
    """
    일봉 최적화 모멘텀 안정형 전략.

    일봉은 노이즈가 적지만 추세 형성이 느리므로,
    골든크로스 + 신고가 돌파 조건으로 강한 상승 추세만 진입.
    넓은 손절/익절로 일봉 변동폭 수용.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 신호 임계값 (일봉 완화)
        self.rsi_threshold = 52
        self.adx_threshold = 18
        self.volume_multiplier = 1.5

        # 출구 파라미터 (넓은 손절/익절)
        self.atr_sl_multiplier = 2.5
        self.atr_tp_multiplier = 5.0
        self.trailing_stop_multiplier = 3.0

        # 풀백 ADX 임계값
        self.pullback_adx_threshold = 25

        # 최근 N봉 최고가 돌파 조건
        self.breakout_lookback = 5

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col,
            'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 추세 필터 1: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 추세 필터 2: 골든크로스 (EMA_50 > EMA_200)
        if current['EMA_50'] <= current['EMA_200']:
            return False

        # 최근 N봉 최고 종가 돌파 확인
        lookback_start = max(0, current_idx - self.breakout_lookback)
        recent_closes = df.iloc[lookback_start:current_idx]['close']
        if len(recent_closes) == 0:
            return False
        highest_recent_close = recent_closes.max()

        # 브레이크아웃 신호 (위크 필터 없음 + 신고가 돌파)
        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
            and current['close'] > highest_recent_close
        )

        # 풀백 신호 (골든크로스 환경에서만)
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
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
