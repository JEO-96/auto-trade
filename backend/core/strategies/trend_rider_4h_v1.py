import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class TrendRider4hV1Strategy(BaseStrategy):
    """
    Trend Rider 4h V1 - 4시간봉 추세 추종 전략 (고정 버전, 수정 금지)

    트레일링 스탑으로 추세를 끝까지 타는 전략.
    TP 없이 고점 대비 5% 하락 시 청산 (추세 추종).

    진입 신호 (OR 조건):
    - RSI 눌림목 반등
    - MACD 골든크로스
    - EMA_20 바운스 (가격이 EMA_20 아래에서 위로 돌파)

    공통 필터:
    - EMA 정배열 (EMA_20 > EMA_50)
    - MACD > Signal
    - RSI < 75 (과열 제외)
    - ADX > 15 (횡보장 제외)
    - 거래량 > 평균
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 4h 손익 파라미터 (소폭 조정)
        self.atr_sl_multiplier = 1.5      # 손절: ATR 1.5배 (유지)
        self.atr_tp_multiplier = 3.5      # 익절: 리스크의 3.5배 (기존 3.0 -> 3.5)
        self.trailing_stop_multiplier = 2.0  # 트레일링: ATR 2.0배 (유지)

        # 트레일링 스탑 모드: 고점 대비 5% 하락 시 청산, TP 없음 (추세 추종)
        self.backtest_sl_pct = 0.05   # 고점 대비 5% 트레일링 스탑
        self.backtest_tp_pct = None   # TP 없음
        self.backtest_trailing = True  # 트레일링 모드 활성화

        # 텔레그램 체크리스트 필터
        self.filter_ema20_gt_ema50 = True
        self.filter_close_gt_ema20 = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 75
        self.filter_adx_min = 15
        self.filter_volume_min = 1.0

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, 'EMA_50', 'EMA_20',
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

        # ========== 공통 필터 (반드시 통과해야 함) ==========

        # 1. EMA 정배열: EMA_20 > EMA_50 (상승 추세)
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 2. 가격이 EMA_20 위 (추세 안에 있음)
        if current['close'] < current['EMA_20']:
            return False

        # 3. MACD가 시그널 위 (상승 모멘텀)
        if macd_val <= macds_val:
            return False

        # 4. RSI 과열 아님 (75 유지)
        if rsi_curr > 75:
            return False

        # 5. ADX > 15 (가벼운 추세 필터, 횡보장 제외)
        if current[self.adx_col] < 15:
            return False

        # 6. 거래량 평균 이상
        if current['volume'] < current[self.vol_ma_col]:
            return False

        # ========== 진입 신호 (하나만 충족하면 됨) ==========

        # 신호 1: RSI 눌림목 반등
        signal_rsi_bounce = (
            rsi_prev < 50 and
            rsi_curr > rsi_prev
        )

        # 신호 2: MACD 골든크로스 (방금 돌파)
        signal_macd_cross = False
        if prev_macd is not None and prev_macds is not None:
            if not pd.isna(prev_macd) and not pd.isna(prev_macds):
                signal_macd_cross = (
                    prev_macd <= prev_macds and
                    macd_val > macds_val
                )

        # 신호 3: EMA_20 바운스 (가격이 EMA_20 아래에서 위로 복귀)
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

        # 신호 1: RSI 눌림목 반등
        rsi_curr = _val(current, self.rsi_col)
        rsi_prev = _val(prev, self.rsi_col)
        if rsi_curr is not None and rsi_prev is not None:
            prev_below = rsi_prev < 50
            curr_rising = rsi_curr > rsi_prev
            is_met = prev_below and curr_rising
            triggers.append(("🔹 RSI 눌림목 반등", bool(is_met)))
            triggers.append((f"    이전RSI<50: {rsi_prev:.1f}", bool(prev_below)))
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
            triggers.append((f"    이전종가 {prev_close:,.0f} {'<' if prev_below else '≥'} EMA20 {prev_ema20:,.0f}", bool(prev_below)))
            triggers.append((f"    현재가 {curr_price:,.0f} {'>' if curr_above else '≤'} EMA20 {curr_ema20:,.0f}", bool(curr_above)))

        return triggers

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)

        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)

        return stop_loss, take_profit
