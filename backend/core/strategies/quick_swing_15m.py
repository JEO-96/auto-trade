"""
QuickSwing15mStrategy - 15분봉 퀵 스윙 전략

빠른 익절 + 엄격한 진입 + 높은 승률:
- EMA_20 > EMA_50 정배열 + EMA_200 매크로
- ADX > 18, MACD > signal
- RSI 과열 74 (엄격)
- OR 조건 3신호: RSI 반등, MACD 크로스, EMA_20 바운스
- 트레일링 스탑 1.8% (빠른 수익 확보)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class QuickSwing15mStrategy(BaseStrategy):
    """15분봉 퀵 스윙 전략 (빠른 익절, 높은 승률)."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 진입 파라미터 (최적화: ADX 25로 강한 추세, RSI 35 눌림목)
        self.rsi_bounce_threshold = 35
        self.adx_threshold = 25
        self.rsi_upper_limit = 74

        # 출구 파라미터 (실매매용 ATR 기반)
        self.atr_sl_multiplier = 1.2
        self.atr_tp_multiplier = 2.0
        self.trailing_stop_multiplier = 1.5

        # 트레일링 스탑 모드
        self.backtest_sl_pct = 0.020   # 2.0% trailing stop
        self.backtest_tp_pct = None    # TP 없음
        self.backtest_trailing = True

        # 텔레그램 체크리스트 필터
        self.filter_ema20_gt_ema50 = True
        self.filter_close_gt_ema200 = True
        self.filter_close_gt_ema20 = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 74
        self.filter_adx_min = 25
        self.filter_volume_min = 1.0

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
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

        # 매크로 상승 추세: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 가격 > EMA_20
        if current['close'] < current['EMA_20']:
            return False

        # MACD > signal
        if macd_val <= macds_val:
            return False

        # RSI 과열 방지
        if rsi_curr > self.rsi_upper_limit:
            return False

        # ADX 최소 추세
        if current[self.adx_col] < self.adx_threshold:
            return False

        # 거래량 평균 이상
        if current['volume'] < current[self.vol_ma_col]:
            return False

        # ========== 진입 신호 (OR 조건) ==========

        # 신호 1: RSI 눌림목 반등
        signal_rsi_bounce = (
            rsi_prev < self.rsi_bounce_threshold and
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
            prev_below = rsi_prev < self.rsi_bounce_threshold
            curr_rising = rsi_curr > rsi_prev
            is_met = prev_below and curr_rising
            triggers.append(("🔹 RSI 눌림목 반등", bool(is_met)))
            triggers.append((f"    이전RSI<{self.rsi_bounce_threshold}: {rsi_prev:.1f}", bool(prev_below)))
            triggers.append((f"    RSI상승: {rsi_prev:.1f}(이전)→{rsi_curr:.1f}(현재) ({'↑' if curr_rising else '↓'})", bool(curr_rising)))

        # 신호 2: MACD 골든크로스
        macd_curr = _val(current, self.macd_col)
        macds_curr = _val(current, self.macds_col)
        macd_prev = _val(prev, self.macd_col)
        macds_prev = _val(prev, self.macds_col)
        if all(v is not None for v in (macd_curr, macds_curr, macd_prev, macds_prev)):
            prev_below = macd_prev <= macds_prev
            curr_above = macd_curr > macds_curr
            is_met = prev_below and curr_above
            triggers.append(("🔹 MACD 골든크로스", bool(is_met)))
            triggers.append((f"    이전MACD≤시그널: {macd_prev:,.0f}(이전MACD) {'≤' if prev_below else '>'} {macds_prev:,.0f}(시그널)", bool(prev_below)))
            triggers.append((f"    현재MACD>시그널: {macd_curr:,.0f}(현재MACD) {'>' if curr_above else '≤'} {macds_curr:,.0f}(시그널)", bool(curr_above)))

        # 신호 3: EMA_20 바운스
        prev_close = _val(prev, 'close')
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        if prev_close is not None and prev_ema20 is not None and curr_ema20 is not None:
            prev_below = prev_close < prev_ema20
            curr_above = curr_price > curr_ema20
            is_met = prev_below and curr_above
            triggers.append(("🔹 EMA20 바운스", bool(is_met)))
            triggers.append((f"    이전종가<EMA20: {prev_close:,.0f}(이전종가) {'<' if prev_below else '≥'} {prev_ema20:,.0f}(EMA20)", bool(prev_below)))
            triggers.append((f"    현재가>EMA20: {curr_price:,.0f}(현재가) {'>' if curr_above else '≤'} {curr_ema20:,.0f}(EMA20)", bool(curr_above)))

        return triggers

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
