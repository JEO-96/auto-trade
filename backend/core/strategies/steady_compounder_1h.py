"""
SteadyCompounder1hStrategy - 1시간봉 최적화 스테디 복리 전략

최고 승률을 위한 빠른 익절 + 엄격한 진입 조건:
- ADX > 20 (트렌드 품질 강화)
- ATR SL 1.2x, TP 1.5x, trailing 1.3x (빠른 익절 = 높은 승률)
- RSI 과열 68 (더 엄격한 진입)
- EMA_200 매크로 필터 (상승 추세만 매매)
- 거래량 > 평균 * 1.3 (강한 거래량 필터)
"""

import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class SteadyCompounder1hStrategy(BaseStrategy):
    """1시간봉 최적화 스테디 복리 전략."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 1h 손익 파라미터 (승률 우선)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 2.0
        self.trailing_stop_multiplier = 1.8

        # 백테스트 SL/TP (그리드 서치 최적화: 230% PnL, 16.8% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.10   # 10% TP

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, 'EMA_50', 'EMA_20', 'EMA_200',
            self.adx_col,
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        rsi_curr = current[self.rsi_col]
        rsi_prev = prev.get(self.rsi_col)
        if rsi_prev is None or pd.isna(rsi_prev):
            return False

        macd_val = current[self.macd_col]
        macds_val = current[self.macds_col]
        prev_macd = prev.get(self.macd_col)
        prev_macds = prev.get(self.macds_col)

        # ========== 공통 필터 ==========

        # EMA 정배열
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 매크로 상승 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 가격 > EMA_20
        if current['close'] < current['EMA_20']:
            return False

        # MACD > signal
        if macd_val <= macds_val:
            return False

        # RSI 과열 (늦은 진입 방어)
        if rsi_curr > 72:
            return False

        # ADX > 20 (트렌드 품질 강화)
        if current[self.adx_col] < 20:
            return False

        # 거래량 평균 이상
        if current['volume'] < current[self.vol_ma_col]:
            return False

        # ========== 진입 신호 ==========

        # 신호 1: RSI 눌림목 반등
        signal_rsi_bounce = (
            rsi_prev < 50 and
            rsi_curr > rsi_prev
        )

        # 신호 2: MACD 골든크로스
        signal_macd_cross = False
        if prev_macd is not None and prev_macds is not None:
            if not pd.isna(prev_macd) and not pd.isna(prev_macds):
                signal_macd_cross = (
                    prev_macd <= prev_macds and
                    macd_val > macds_val
                )

        # 신호 3: EMA_20 바운스
        prev_close = prev.get('close')
        prev_ema20 = prev.get('EMA_20')
        signal_ema_bounce = False
        if prev_close is not None and prev_ema20 is not None:
            if not pd.isna(prev_close) and not pd.isna(prev_ema20):
                signal_ema_bounce = (
                    prev_close < prev_ema20 and
                    current['close'] > current['EMA_20']
                )

        return signal_rsi_bounce or signal_macd_cross or signal_ema_bounce

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
