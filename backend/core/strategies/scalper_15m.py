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

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema20_gt_ema50 = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 75
        self.filter_adx_min = 25
        self.filter_volume_min = 1.0

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
            prev_below = rsi_prev < self.rsi_threshold
            curr_rising = rsi_curr > rsi_prev
            is_met = prev_below and curr_rising
            triggers.append(("🔹 RSI 눌림목 반등", bool(is_met)))
            triggers.append((f"    이전RSI<{self.rsi_threshold}: {rsi_prev:.1f}", bool(prev_below)))
            triggers.append((f"    RSI 상승: {rsi_prev:.1f}→{rsi_curr:.1f}", bool(curr_rising)))

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
            triggers.append((f"    이전: MACD {macd_prev:.2f} {'≤' if prev_below else '>'} 시그널 {macds_prev:.2f}", bool(prev_below)))
            triggers.append((f"    현재: MACD {macd_curr:.2f} {'>' if curr_above else '≤'} 시그널 {macds_curr:.2f}", bool(curr_above)))

        # 신호 3: EMA_20 바운스
        prev_close = _val(prev, 'close')
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        if prev_close is not None and prev_ema20 is not None and curr_ema20 is not None:
            prev_below = prev_close < prev_ema20
            curr_above = curr_price > curr_ema20
            is_met = prev_below and curr_above
            triggers.append(("🔹 EMA20 바운스", bool(is_met)))
            triggers.append((f"    이전종가<EMA20: {prev_close:,.0f} / {prev_ema20:,.0f}", bool(prev_below)))
            triggers.append((f"    현재가>EMA20: {curr_price:,.0f} / {curr_ema20:,.0f}", bool(curr_above)))

        return triggers

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
