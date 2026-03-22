import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class TrendRider4hV3Strategy(BaseStrategy):
    """
    Trend Rider 4h V3 - 4시간봉 추세 추종 전략 (공격적 튜닝)

    V1 대비 변경점:
    - 트리거 신호 6개로 확장 (V1: 3개)
      → 볼린저 밴드 하단 반등, 스토캐스틱 골든크로스, 강세 장악형 캔들 추가
    - RSI 눌림목 기준 완화 (50→55): 더 많은 진입 기회
    - 트레일링 스탑 3.5% (V1: 5%): 수익 보존 강화
    - ADX 12 (V1: 15): 약한 추세에서도 진입
    - 거래량 0.8x (V1: 1.0x): 약간 완화
    - MACD 필터 제거 (V2와 동일)
    - RSI 상한 78 (V1: 75): 강한 추세 진입 허용

    공통 필터:
    - EMA 정배열 (EMA_20 > EMA_50)
    - 가격 > EMA_20
    - RSI < 78
    - ADX > 12
    - 거래량 > 평균 × 0.8

    진입 신호 (OR 조건):
    1. RSI 눌림목 반등 (이전 < 55, 현재 상승)
    2. MACD 골든크로스
    3. EMA_20 바운스
    4. 볼린저 밴드 하단 반등
    5. 스토캐스틱 골든크로스 (과매도 탈출)
    6. 강세 장악형 캔들 (Bullish Engulfing)
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 4h 손익 파라미터
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.0

        # 트레일링 스탑 모드: 고점 대비 3.5% 하락 시 청산
        self.backtest_sl_pct = 0.035    # V1: 0.05 → V3: 0.035
        self.backtest_tp_pct = None
        self.backtest_trailing = True

        # 볼린저 밴드 파라미터
        self.bb_period = 20
        self.bb_std = 2.0

        # 스토캐스틱 파라미터
        self.stoch_k = 14
        self.stoch_d = 3
        self.stoch_smooth_k = 3

        # 텔레그램 체크리스트 필터
        self.filter_ema20_gt_ema50 = True
        self.filter_close_gt_ema20 = True
        self.filter_macd_gt_signal = False    # MACD 필터 제거
        self.filter_rsi_max = 78              # V1: 75 → V3: 78
        self.filter_adx_min = 12              # V1: 15 → V3: 12
        self.filter_volume_min = 0.8          # V1: 1.0 → V3: 0.8

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기본 지표 + 볼린저 밴드 + 스토캐스틱 추가"""
        df = super().apply_indicators(df)

        # 볼린저 밴드
        bb = df.ta.bbands(length=self.bb_period, std=self.bb_std)
        if bb is not None:
            bb_cols = bb.columns
            for col in bb_cols:
                if 'BBL' in col:
                    df['BB_LOWER'] = bb[col]
                elif 'BBM' in col:
                    df['BB_MID'] = bb[col]
                elif 'BBU' in col:
                    df['BB_UPPER'] = bb[col]

        # 스토캐스틱
        stoch = df.ta.stoch(k=self.stoch_k, d=self.stoch_d, smooth_k=self.stoch_smooth_k)
        if stoch is not None:
            stoch_cols = stoch.columns
            for col in stoch_cols:
                if col.startswith('STOCHk'):
                    df['STOCH_K'] = stoch[col]
                elif col.startswith('STOCHd'):
                    df['STOCH_D'] = stoch[col]

        return df

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

        # ========== 공통 필터 ==========

        # 1. EMA 정배열: EMA_20 > EMA_50
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 2. 가격이 EMA_20 위
        if current['close'] < current['EMA_20']:
            return False

        # 3. RSI 과열 제외
        if rsi_curr > 78:
            return False

        # 4. ADX > 12
        if current[self.adx_col] < 12:
            return False

        # 5. 거래량 >= 평균 × 0.8
        if current['volume'] < current[self.vol_ma_col] * 0.8:
            return False

        # ========== 진입 신호 (하나만 충족하면 됨) ==========

        # 신호 1: RSI 눌림목 반등 (기준 완화: 50→55)
        signal_rsi_bounce = (
            rsi_prev < 55 and
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

        # 신호 4: 볼린저 밴드 하단 반등
        signal_bb_bounce = False
        bb_lower = current.get('BB_LOWER')
        prev_bb_lower = prev.get('BB_LOWER')
        if bb_lower is not None and prev_bb_lower is not None:
            if not pd.isna(bb_lower) and not pd.isna(prev_bb_lower):
                prev_close_val = prev.get('close')
                if prev_close_val is not None and not pd.isna(prev_close_val):
                    signal_bb_bounce = (
                        prev_close_val <= prev_bb_lower * 1.01 and
                        current['close'] > bb_lower
                    )

        # 신호 5: 스토캐스틱 골든크로스 (과매도 탈출)
        signal_stoch_cross = False
        stoch_k = current.get('STOCH_K')
        stoch_d = current.get('STOCH_D')
        prev_stoch_k = prev.get('STOCH_K')
        prev_stoch_d = prev.get('STOCH_D')
        if all(v is not None and not pd.isna(v) for v in [stoch_k, stoch_d, prev_stoch_k, prev_stoch_d]):
            signal_stoch_cross = (
                prev_stoch_k <= prev_stoch_d and
                stoch_k > stoch_d and
                stoch_k < 80  # 과매수 진입 방지
            )

        # 신호 6: 강세 장악형 캔들 (Bullish Engulfing)
        signal_engulfing = False
        prev_open = prev.get('open')
        prev_close_val = prev.get('close')
        curr_open = current.get('open')
        curr_close = current.get('close')
        if all(v is not None and not pd.isna(v) for v in [prev_open, prev_close_val, curr_open, curr_close]):
            prev_bearish = prev_close_val < prev_open  # 이전 음봉
            curr_bullish = curr_close > curr_open       # 현재 양봉
            engulf = curr_close > prev_open and curr_open <= prev_close_val  # 장악
            body_size = abs(curr_close - curr_open)
            avg_body = df['close'].iloc[max(0, current_idx-20):current_idx].std()
            if avg_body > 0:
                signal_engulfing = (
                    prev_bearish and curr_bullish and engulf and
                    body_size > avg_body * 0.5
                )

        return (signal_rsi_bounce or signal_macd_cross or signal_ema_bounce or
                signal_bb_bounce or signal_stoch_cross or signal_engulfing)

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
            prev_below = rsi_prev < 55
            curr_rising = rsi_curr > rsi_prev
            is_met = prev_below and curr_rising
            triggers.append(("🔹 RSI 눌림목 반등", bool(is_met)))
            triggers.append((f"    이전RSI<55: {rsi_prev:.1f}(이전RSI) {'<' if prev_below else '≥'} 55", bool(prev_below)))
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

        # 신호 4: 볼린저 밴드 하단 반등
        bb_lower = _val(current, 'BB_LOWER')
        prev_bb_lower = _val(prev, 'BB_LOWER')
        prev_close_val = _val(prev, 'close')
        if bb_lower is not None and prev_bb_lower is not None and prev_close_val is not None:
            prev_near_bb = prev_close_val <= prev_bb_lower * 1.01
            curr_above_bb = curr_price > bb_lower
            is_met = prev_near_bb and curr_above_bb
            triggers.append(("🔹 BB 하단 반등", bool(is_met)))
            triggers.append((f"    이전종가≤BB하단: {prev_close_val:,.0f}(이전종가) {'≤' if prev_near_bb else '>'} {prev_bb_lower * 1.01:,.0f}(BB하단)", bool(prev_near_bb)))
            triggers.append((f"    현재가>BB하단: {curr_price:,.0f}(현재가) {'>' if curr_above_bb else '≤'} {bb_lower:,.0f}(BB하단)", bool(curr_above_bb)))

        # 신호 5: 스토캐스틱 골든크로스
        stoch_k = _val(current, 'STOCH_K')
        stoch_d = _val(current, 'STOCH_D')
        prev_stoch_k = _val(prev, 'STOCH_K')
        prev_stoch_d = _val(prev, 'STOCH_D')
        if all(v is not None for v in (stoch_k, stoch_d, prev_stoch_k, prev_stoch_d)):
            prev_below = prev_stoch_k <= prev_stoch_d
            curr_cross = stoch_k > stoch_d
            not_overbought = stoch_k < 80
            is_met = prev_below and curr_cross and not_overbought
            triggers.append(("🔹 스토캐스틱 크로스", bool(is_met)))
            triggers.append((f"    이전K≤D: {prev_stoch_k:.1f}(K) {'≤' if prev_below else '>'} {prev_stoch_d:.1f}(D)", bool(prev_below)))
            triggers.append((f"    현재K>D: {stoch_k:.1f}(K) {'>' if curr_cross else '≤'} {stoch_d:.1f}(D)", bool(curr_cross)))
            triggers.append((f"    K<80: {stoch_k:.1f}(K) {'<' if not_overbought else '≥'} 80", bool(not_overbought)))

        # 신호 6: 강세 장악형 캔들
        prev_open = _val(prev, 'open')
        prev_close_v = _val(prev, 'close')
        curr_open = _val(current, 'open')
        if prev_open is not None and prev_close_v is not None and curr_open is not None:
            prev_bearish = prev_close_v < prev_open
            curr_bullish = curr_price > curr_open
            engulf = curr_price > prev_open and curr_open <= prev_close_v
            is_met = prev_bearish and curr_bullish and engulf
            triggers.append(("🔹 강세 장악형 캔들", bool(is_met)))
            triggers.append((f"    이전 음봉: 종가 {prev_close_v:,.0f} < 시가 {prev_open:,.0f}", bool(prev_bearish)))
            triggers.append((f"    현재 양봉: 종가 {curr_price:,.0f} > 시가 {curr_open:,.0f}", bool(curr_bullish)))
            triggers.append((f"    장악: 현재종가>이전시가, 현재시가≤이전종가", bool(engulf)))

        return triggers

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)

        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)

        return stop_loss, take_profit
