"""
Scalper15mStrategy - 15분봉 트레일링 스캘핑 전략

고빈도 + 트레일링 스탑 추세 추종:
- RSI 45 + ADX 18 (적절한 진입 조건)
- 볼륨 1.0x (최소 평균 이상)
- EMA_200 매크로 필터 + EMA_20 > EMA_50 정배열
- OR 기반 3신호: RSI 반등, MACD 크로스, EMA_20 바운스
- 트레일링 스탑 2.0% (고점 대비 하락 시 청산, TP 없음)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class Scalper15mStrategy(BaseStrategy):
    """
    15분봉 트레일링 스캘핑 전략.

    15분봉 데이터 풍부 (하루 96봉) + 트레일링 스탑으로
    짧은 추세도 최대한 포착. EMA 정배열 필터로 노이즈 감소.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 신호 임계값 (최적화: ADX 25로 강한 추세만 포착)
        self.rsi_threshold = 30
        self.adx_threshold = 25
        self.volume_multiplier = 1.0

        # 출구 파라미터 (실매매용 ATR 기반)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 3.0
        self.trailing_stop_multiplier = 2.0

        # 트레일링 스탑 모드 (고점 대비 2% 하락 시 청산)
        self.backtest_sl_pct = 0.020   # 2.0% trailing stop
        self.backtest_tp_pct = None    # TP 없음 (추세 추종)
        self.backtest_trailing = True

        # RSI 과열 상한
        self.rsi_upper_limit = 75

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

        rsi_curr = current[self.rsi_col]
        rsi_prev = prev.get(self.rsi_col)
        if rsi_prev is None or pd.isna(rsi_prev):
            return False

        # 매크로 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # EMA 정배열: EMA_20 > EMA_50 (추세 품질 필터)
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # RSI 과열 방지
        if rsi_curr > self.rsi_upper_limit:
            return False

        # MACD > signal (기본 방향성 확인)
        if current[self.macd_col] <= current[self.macds_col]:
            return False

        # 최소 거래량
        if current['volume'] < current[self.vol_ma_col] * self.volume_multiplier:
            return False

        # ADX 최소 추세 강도
        if current[self.adx_col] < self.adx_threshold:
            return False

        # ========== 진입 신호 (OR 조건) ==========

        # 신호 1: RSI 눌림목 반등
        signal_rsi_bounce = (
            rsi_prev < self.rsi_threshold
            and rsi_curr > rsi_prev
        )

        # 신호 2: MACD 골든크로스
        prev_macd = prev.get(self.macd_col)
        prev_macds = prev.get(self.macds_col)
        signal_macd_cross = False
        if prev_macd is not None and prev_macds is not None:
            if not pd.isna(prev_macd) and not pd.isna(prev_macds):
                signal_macd_cross = (
                    prev_macd <= prev_macds
                    and current[self.macd_col] > current[self.macds_col]
                )

        # 신호 3: EMA_20 바운스
        prev_close = prev.get('close')
        prev_ema20 = prev.get('EMA_20')
        signal_ema_bounce = False
        if prev_close is not None and prev_ema20 is not None:
            if not pd.isna(prev_close) and not pd.isna(prev_ema20):
                signal_ema_bounce = (
                    prev_close < prev_ema20
                    and current['close'] > current['EMA_20']
                )

        return signal_rsi_bounce or signal_macd_cross or signal_ema_bounce

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
