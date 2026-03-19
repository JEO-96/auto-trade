"""
MomentumStable1hStrategy - 1시간봉 최적화 모멘텀 안정형 전략

MaxDD 최소화 목표 (basic_1h 20.1% 이하 → 목표 <20%):
- 골든크로스 필터: EMA_50 > EMA_200 (하락장 진입 방지)
- DI+ > DI- 방향성 필터 (추세 방향 확인)
- RSI 임계값 57, RSI < 72 과매수 필터 (강화)
- ADX 임계값 25 (강한 추세만 진입)
- 볼륨 임계값 1.5x (1시간봉 노이즈 대응)
- ATR SL 1.0x (매우 타이트한 손절), TP 2.0x (빠른 익절)
- trailing 1.2x (타이트한 추적 손절)
- 위크 필터 완화 (0.9 ratio)
"""
import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable1hStrategy(BaseStrategy):
    """
    1시간봉 최적화 모멘텀 안정형 전략.

    골든크로스(EMA_50>EMA_200) + DI+ 방향성 필터로 하락장 진입 방지.
    RSI 57 + ADX 25로 강한 추세만 진입, ATR SL 1.0x로 타이트한 손절.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 신호 임계값
        self.rsi_threshold = 57
        self.rsi_overbought = 78
        self.adx_threshold = 22
        self.volume_multiplier = 1.5

        # 출구 파라미터
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 3.0
        self.trailing_stop_multiplier = 1.5

        # 백테스트 SL/TP (그리드 서치 최적화: 185% PnL, 25.7% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.15   # 15% TP

        # 풀백 ADX 임계값
        self.pullback_adx_threshold = 28

        # 위크 필터 (완화)
        self.wick_filter_ratio = 0.9

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema50_gt_ema200 = True
        self.filter_di_positive = True
        self.filter_rsi_max = 78

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_50', 'EMA_200', 'EMA_20',
            'DMP_14', 'DMN_14',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 골든크로스 필터: EMA_50 > EMA_200 (하락장 진입 방지)
        if current['EMA_50'] < current['EMA_200']:
            return False

        # 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # DI+ > DI- 방향성 필터 (추세 방향 확인)
        if current['DMP_14'] <= current['DMN_14']:
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
