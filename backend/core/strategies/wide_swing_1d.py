"""
WideSwing1dStrategy - 일봉 와이드 스윙 전략

넓은 SL/TP로 일봉 변동성을 수용하는 스윙 트레이딩:
- ADX > 13 (일봉은 추세가 강해 낮은 임계값)
- ATR SL 2.0x, TP 4.0x, trailing 2.5x (넓은 스윙)
- RSI 과열 78
- EMA_200 추세 필터
- OR 조건 3신호: RSI 반등, MACD 크로스, EMA_20 바운스
"""

import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class WideSwing1dStrategy(BaseStrategy):
    """일봉 와이드 스윙 전략 (넓은 SL/TP, 일봉 변동성 수용)."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 1d 손익 파라미터
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 4.0
        self.trailing_stop_multiplier = 2.5

        # 백테스트 SL/TP
        self.backtest_sl_pct = 0.04   # 4% SL
        self.backtest_tp_pct = 0.20   # 20% TP

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema20_gt_ema50 = True
        self.filter_close_gt_ema20 = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 78
        self.filter_adx_min = 13
        self.filter_volume_min = 1.0

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, 'EMA_200', 'EMA_50', 'EMA_20',
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

        # EMA_200 위 (장기 추세 필터)
        if current['close'] < current['EMA_200']:
            return False

        # EMA 정배열
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 가격 > EMA_20
        if current['close'] < current['EMA_20']:
            return False

        # MACD > signal
        if macd_val <= macds_val:
            return False

        # RSI 과열
        if rsi_curr > 78:
            return False

        # ADX > 13 (가벼운 추세 필터)
        if current[self.adx_col] < 13:
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

    def get_trigger_signals(
        self, df: pd.DataFrame, current_idx: int, curr_price: float
    ) -> list[tuple[str, bool]]:
        if current_idx < 1:
            return []

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        def _val(row, col):
            v = row.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            return v

        triggers: list[tuple[str, bool]] = []

        rsi_curr = _val(current, self.rsi_col)
        rsi_prev = _val(prev, self.rsi_col)

        # 신호 1: RSI 눌림목 반등
        if rsi_curr is not None and rsi_prev is not None:
            is_met = rsi_prev < 50 and rsi_curr > rsi_prev
            triggers.append((f"RSI눌림목 (이전:{rsi_prev:.1f} 현재:{rsi_curr:.1f})", bool(is_met)))

        # 신호 2: MACD 골든크로스
        macd_curr = _val(current, self.macd_col)
        macds_curr = _val(current, self.macds_col)
        macd_prev = _val(prev, self.macd_col)
        macds_prev = _val(prev, self.macds_col)
        if all(v is not None for v in (macd_curr, macds_curr, macd_prev, macds_prev)):
            is_met = macd_prev <= macds_prev and macd_curr > macds_curr
            triggers.append(("MACD 골든크로스", bool(is_met)))

        # 신호 3: EMA_20 바운스
        prev_close = _val(prev, 'close')
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        if prev_close is not None and prev_ema20 is not None and curr_ema20 is not None:
            is_met = prev_close < prev_ema20 and curr_price > curr_ema20
            triggers.append(("EMA20 바운스", bool(is_met)))

        return triggers

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
