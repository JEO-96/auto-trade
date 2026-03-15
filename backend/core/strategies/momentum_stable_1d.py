"""
MomentumStable1dStrategy - 일봉 최적화 모멘텀 안정형 전략

MaxDD 최소화 목표 (basic_1d 6.3% 이하 → 목표 <6%):
- 볼륨 임계값 1.5x (일봉 변동폭 대응)
- RSI 임계값 55, RSI 상한 78
- ADX 임계값 25 (강화: 22→25, 매우 강한 추세만 진입)
- DI+ > DI- 방향성 필터
- ATR SL 1.5x, TP 2.5x, trailing 1.8x (매우 타이트한 손절/익절)
- EMA_50 > EMA_200 골든크로스 필터
- 최근 5봉 최고 종가 돌파 조건

v3 변경사항 (MaxDD 추가 감소):
- ADX 22→25, pullback ADX 25→28
- ATR SL 2.0→1.5, TP 3.5→2.5, trailing 2.5→1.8
"""
import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable1dStrategy(BaseStrategy):
    """
    일봉 최적화 모멘텀 안정형 전략.

    일봉은 노이즈가 적지만 추세 형성이 느리므로,
    골든크로스 + 신고가 돌파 + DI+ 방향성 확인으로 강한 상승 추세만 진입.
    타이트한 손절/익절로 낮은 MaxDD 유지 (안정형 핵심 목표).
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 신호 임계값
        self.rsi_threshold = 55
        self.rsi_upper_limit = 78
        self.adx_threshold = 22
        self.volume_multiplier = 1.5

        # 출구 파라미터
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.5

        # 백테스트 SL/TP (그리드 서치 최적화: 31% PnL, 10.8% MaxDD)
        self.backtest_sl_pct = 0.02   # 2% SL
        self.backtest_tp_pct = 0.20   # 20% TP

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
            self.dmp_col, self.dmn_col,
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

        # 방향성 필터: DI+ > DI- (상승 추세 확인)
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # 과매수 방지: RSI 상한
        if current[self.rsi_col] > self.rsi_upper_limit:
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
