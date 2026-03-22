"""
TrendFollower15mStrategy - 15분봉 순수 추세추종 전략

순수 추세 추종 (새 컨셉):
- EMA_20 > EMA_50 > EMA_200 3중 정배열 필수
- DI+ > DI- + ADX 22+ (강한 추세만)
- RSI 50~72 밴드 (추세 유지 구간만)
- 가격이 EMA_20 위에서 반등할 때 진입
- 넓은 트레일링 스탑 2.5% (추세 최대 추종)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class TrendFollower15mStrategy(BaseStrategy):
    """
    15분봉 순수 추세추종 전략.

    3중 EMA 정배열 + DI 방향성으로 강한 상승 추세만 포착.
    넓은 트레일링 스탑으로 추세를 최대한 추종.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = False

        # 출구 파라미터 (실매매용 ATR 기반)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 2.5
        self.trailing_stop_multiplier = 2.5

        # 고정 SL/TP 모드 (최적화: FIXED 1.2/3.0%가 TRAIL 4.0% 대비 +54.8% 개선)
        self.backtest_sl_pct = 0.012   # 1.2% stop loss
        self.backtest_tp_pct = 0.030   # 3.0% take profit
        self.backtest_trailing = False

        # 진입 조건 (최적화: ADX 25+, RSI 30-68, EMA 0.2%로 타이트)
        self.adx_threshold = 25
        self.rsi_lower = 30
        self.rsi_upper = 68
        self.ema_proximity_pct = 0.002  # EMA_20 근접 판단 기준 (0.2%)

        # 텔레그램 체크리스트 필터
        self.filter_triple_ema = True
        self.filter_close_gt_ema20 = True
        self.filter_di_positive = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 68
        self.filter_adx_min = 25

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.adx_col,
            self.dmp_col, self.dmn_col,
            'EMA_200', 'EMA_50', 'EMA_20',
            self.macd_col, self.macds_col,
        ]
        if not self._validate_indicators(current, required_cols):
            return False

        # 3중 EMA 정배열: EMA_20 > EMA_50 > EMA_200
        if not (current['EMA_20'] > current['EMA_50'] > current['EMA_200']):
            return False

        # 가격 > EMA_20
        if current['close'] < current['EMA_20']:
            return False

        # DI+ > DI- (상승 추세)
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # ADX 강한 추세
        if current[self.adx_col] < self.adx_threshold:
            return False

        # RSI 추세 유지 밴드 (50~72)
        rsi = current[self.rsi_col]
        if rsi < self.rsi_lower or rsi > self.rsi_upper:
            return False

        # MACD > signal
        if current[self.macd_col] <= current[self.macds_col]:
            return False

        # 진입 트리거: 이전 봉이 EMA_20 근처에서 반등
        prev_ema20 = prev.get('EMA_20')
        if prev_ema20 is None or pd.isna(prev_ema20):
            return False

        # 이전 봉 저가가 EMA_20에 근접 또는 이전 봉 종가 < EMA_20
        ema20_proximity = abs(prev['low'] - prev_ema20) / prev_ema20 < self.ema_proximity_pct
        prev_below_ema = prev['close'] < prev_ema20

        return ema20_proximity or prev_below_ema

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

        prev_ema20 = _val(prev, 'EMA_20')
        prev_low = _val(prev, 'low')
        prev_close = _val(prev, 'close')

        # 신호 1: EMA_20 근접 반등 (저가가 EMA_20에 근접)
        if prev_low is not None and prev_ema20 is not None and prev_ema20 > 0:
            proximity = abs(prev_low - prev_ema20) / prev_ema20
            is_met = proximity < self.ema_proximity_pct
            triggers.append(("🔹 EMA20 근접 반등", bool(is_met)))
            triggers.append((f"    저가-EMA20 거리<{self.ema_proximity_pct*100:.1f}%: 현재 {proximity*100:.2f}%", bool(is_met)))
            triggers.append((f"    이전저가 {prev_low:,.0f} ↔ EMA20 {prev_ema20:,.0f}", bool(is_met)))

        # 신호 2: 이전 봉 EMA20 하회 반등
        if prev_close is not None and prev_ema20 is not None:
            is_met = prev_close < prev_ema20
            triggers.append(("🔹 이전봉 EMA20 하회 반등", bool(is_met)))
            triggers.append((f"    이전종가 {prev_close:,.0f} {'<' if is_met else '≥'} EMA20 {prev_ema20:,.0f}", bool(is_met)))

        return triggers

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
