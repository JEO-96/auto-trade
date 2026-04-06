import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class TrendRider4hV4Strategy(BaseStrategy):
    """
    Trend Rider 4h V4 - 알트코인 범용 추세 추종 전략

    V1 대비 핵심 개선:
    1. ATR 기반 적응형 트레일링 스탑 (고정 5% → ATR 2.5배)
       - 변동성 큰 알트코인: 자동으로 넓은 스탑
       - 안정적인 대형 코인: 자동으로 타이트한 스탑
    2. ADX 강화 (15→20) — 약한 추세에서의 false signal 감소
    3. 진입 시 ATR 대비 최소 리워드 확인 — 변동성 대비 충분한 수익 여지
    4. RSI 하한 추가 (30 이상) — 급락 중 역추세 매수 방지

    진입 신호 (OR 조건, V1과 동일 구조):
    - RSI 눌림목 반등 (이전 RSI < 45, 현재 상승)
    - MACD 골든크로스
    - EMA_20 바운스

    공통 필터 (V1보다 강화):
    - EMA 정배열 (EMA_20 > EMA_50)
    - 가격 > EMA_20
    - MACD > Signal
    - 30 < RSI < 70 (과열/과매도 모두 제외)
    - ADX > 20 (V1: 15 → 더 강한 추세만)
    - 거래량 > 평균 * 1.2 (V1: 1.0 → 유동성 확인 강화)
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # ATR 기반 동적 SL/TP
        self.atr_sl_multiplier = 2.5      # 트레일링: ATR 2.5배 (V1: 고정 5%)
        self.atr_tp_multiplier = 4.0      # TP (사용 안 함, 트레일링 모드)
        self.trailing_stop_multiplier = 2.5

        # 백테스트용 — ATR 기반이므로 고정 pct는 폴백용
        # 실제로는 _dynamic_trailing_pct()로 ATR 기반 계산
        self.backtest_sl_pct = 0.07       # 폴백: 7% (V1: 5%)
        self.backtest_tp_pct = None       # TP 없음 (추세 추종)
        self.backtest_trailing = True

        # 강화된 필터 파라미터
        self.rsi_lower = 30               # RSI 하한 (급락 중 매수 방지)
        self.rsi_upper = 70               # RSI 상한 (V1: 75 → 더 보수적)
        self.adx_min = 20                 # ADX 최소 (V1: 15 → 강한 추세만)
        self.volume_ratio = 1.2           # 거래량 배수 (V1: 1.0 → 유동성 강화)
        self.rsi_bounce_threshold = 45    # RSI 눌림목 기준 (V1: 50 → 더 깊은 눌림)

        # 텔레그램 체크리스트 필터
        self.filter_ema20_gt_ema50 = True
        self.filter_close_gt_ema20 = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 70
        self.filter_adx_min = 20
        self.filter_volume_min = 1.2

    def _get_atr_trailing_pct(self, df: pd.DataFrame, idx: int) -> float:
        """ATR 기반 동적 트레일링 스탑 비율 계산.
        ATR / 현재가 * multiplier로 변동성에 비례하는 스탑."""
        atr_val = df.iloc[idx].get(self.atr_col)
        price = df.iloc[idx]['close']

        if atr_val is None or pd.isna(atr_val) or price <= 0:
            return self.backtest_sl_pct  # 폴백

        atr_pct = (atr_val / price) * self.atr_sl_multiplier
        # 최소 3%, 최대 12% 범위로 클램프
        return max(0.03, min(0.12, atr_pct))

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, 'EMA_50', 'EMA_20',
            self.adx_col, self.atr_col,
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

        # ========== 공통 필터 (강화) ==========

        # 1. EMA 정배열: EMA_20 > EMA_50
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 2. 가격 > EMA_20
        if current['close'] < current['EMA_20']:
            return False

        # 3. MACD > Signal
        if macd_val <= macds_val:
            return False

        # 4. RSI 밴드: 30 < RSI < 70 (과열 + 과매도 모두 제외)
        if rsi_curr > self.rsi_upper or rsi_curr < self.rsi_lower:
            return False

        # 5. ADX > 20 (V1: 15 → 더 강한 추세 요구)
        if current[self.adx_col] < self.adx_min:
            return False

        # 6. 거래량 > 평균 * 1.2 (유동성 확인 강화)
        if current['volume'] < current[self.vol_ma_col] * self.volume_ratio:
            return False

        # 7. ATR 대비 최소 리워드 확인 — 변동성이 너무 낮으면 스킵
        atr_val = current.get(self.atr_col)
        if atr_val is not None and not pd.isna(atr_val):
            atr_pct = atr_val / current['close']
            if atr_pct < 0.005:  # ATR이 가격의 0.5% 미만이면 움직임 부족
                return False

        # ========== 진입 신호 (하나만 충족) ==========

        # 신호 1: RSI 눌림목 반등 (더 깊은 눌림 요구)
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

        # ATR 기반 동적 스탑 표시
        atr_val = _val(current, self.atr_col)
        if atr_val is not None:
            trailing_pct = self._get_atr_trailing_pct(df, current_idx) * 100
            triggers.append((f"📐 ATR 트레일링 스탑: {trailing_pct:.1f}% (ATR={atr_val:,.0f})", True))

        # 신호 1: RSI 눌림목 반등
        rsi_curr = _val(current, self.rsi_col)
        rsi_prev = _val(prev, self.rsi_col)
        if rsi_curr is not None and rsi_prev is not None:
            prev_below = rsi_prev < self.rsi_bounce_threshold
            curr_rising = rsi_curr > rsi_prev
            is_met = prev_below and curr_rising
            triggers.append(("🔹 RSI 눌림목 반등", bool(is_met)))
            triggers.append((f"    이전RSI<{self.rsi_bounce_threshold}: {rsi_prev:.1f} {'<' if prev_below else '≥'} {self.rsi_bounce_threshold}", bool(prev_below)))
            triggers.append((f"    RSI상승: {rsi_prev:.1f}→{rsi_curr:.1f} ({'↑' if curr_rising else '↓'})", bool(curr_rising)))

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

        # 신호 3: EMA_20 바운스
        prev_close = _val(prev, 'close')
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        if prev_close is not None and prev_ema20 is not None and curr_ema20 is not None:
            prev_below = prev_close < prev_ema20
            curr_above = curr_price > curr_ema20
            is_met = prev_below and curr_above
            triggers.append(("🔹 EMA20 바운스", bool(is_met)))

        return triggers

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)

        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)

        return stop_loss, take_profit
