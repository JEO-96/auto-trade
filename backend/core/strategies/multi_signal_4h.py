"""
MultiSignal4hStrategy - 4시간봉 전용 멀티시그널 전략

3가지 진입 신호(돌파/추세/풀백)를 조합하는 전략:
- 골든크로스 필터: EMA_50 > EMA_200 (전 시그널 공통)
- DI+ > DI- 방향성 필터 (전 시그널 공통)
- RSI 상한 77 (과매수 진입 방지)
- breakout_adx_min 22, trend_rider_adx_min 26
- ATR TP 4.5 (큰 수익 목표)
- Bull Pullback 볼륨 필터: volume > vol_avg * 1.2
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MultiSignal4hStrategy(BaseStrategy):
    """4시간봉 전용 멀티시그널 전략 (돌파/추세/풀백 3중 신호)."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.volume_ma_period = 20

        # 4h 시그널 임계값
        self.rsi_threshold = 57
        self.rsi_upper_limit = 77
        self.volume_multiplier = 1.5
        self.pullback_volume_multiplier = 1.2

        # ADX 차등 문턱
        self.breakout_adx_min = 22
        self.trend_rider_adx_min = 26
        self.trend_rider_rsi_min = 53

        # Bull Pullback
        self.pullback_rsi_min = 50

        # 4h 출구 파라미터
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 4.5
        self.trailing_stop_multiplier = 2.2

        # 리스크 스케일링
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 1.8
        self.risk_default_multiplier = 1.2

        # 백테스트 SL/TP
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.10   # 10% TP

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema50_gt_ema200 = True
        self.filter_di_positive = True
        self.filter_rsi_max = 77

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = super().apply_indicators(df)
        ema100 = df.ta.ema(length=100)
        df['EMA_100'] = (
            ema100.iloc[:, 0]
            if hasattr(ema100, 'iloc') and ema100.ndim > 1
            else ema100
        )
        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        rsi_val = current.get(self.rsi_col, None)
        adx_val = current.get(self.adx_col, None)
        dmp_val = current.get(self.dmp_col, None)
        dmn_val = current.get(self.dmn_col, None)
        macd_val = current.get(self.macd_col, None)
        macds_val = current.get(self.macds_col, None)
        vol_avg = current.get(self.vol_ma_col, None)
        ema_200 = current.get('EMA_200', None)
        ema_100 = current.get('EMA_100', None)
        ema_50 = current.get('EMA_50', None)
        ema_20 = current.get('EMA_20', None)

        core_vals = [rsi_val, adx_val, dmp_val, dmn_val, macd_val, macds_val, vol_avg, ema_200, ema_100, ema_50, ema_20]
        if any(v is None or pd.isna(v) for v in core_vals):
            return False
        if vol_avg == 0:
            return False

        # === 공통 필터 ===
        if current['close'] <= ema_200:
            return False
        if ema_50 <= ema_200:
            return False
        if dmp_val <= dmn_val:
            return False
        if rsi_val > self.rsi_upper_limit:
            return False

        # 1. CORE BREAKOUT
        breakout = (
            adx_val > self.breakout_adx_min
            and rsi_val > self.rsi_threshold
            and macd_val > macds_val
            and current['volume'] > vol_avg * self.volume_multiplier
            and current['close'] > ema_100
        )

        # 2. TREND RIDER
        trend_rider = False
        prev_ema20 = prev.get('EMA_20', None)
        if prev_ema20 is not None and not pd.isna(prev_ema20):
            trend_rider = (
                adx_val > self.trend_rider_adx_min
                and current['close'] > ema_20
                and prev['close'] < prev_ema20
                and rsi_val > self.trend_rider_rsi_min
            )

        # 3. BULL PULLBACK (볼륨 필터)
        bull_pullback = (
            prev['low'] < ema_50
            and current['close'] > ema_50
            and rsi_val > self.pullback_rsi_min
            and macd_val > macds_val
            and current['volume'] > vol_avg * self.pullback_volume_multiplier
        )

        return breakout or trend_rider or bull_pullback

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

        rsi_val = _val(current, self.rsi_col)
        adx_val = _val(current, self.adx_col)
        macd_val = _val(current, self.macd_col)
        macds_val = _val(current, self.macds_col)
        vol_avg = _val(current, self.vol_ma_col)
        ema_100 = _val(current, 'EMA_100')
        ema_50 = _val(current, 'EMA_50')
        ema_20 = _val(current, 'EMA_20')
        vol = _val(current, 'volume')

        # 신호 1: CORE BREAKOUT
        if all(v is not None for v in (adx_val, rsi_val, macd_val, macds_val, vol, vol_avg, ema_100)) and vol_avg > 0:
            adx_ok = adx_val > self.breakout_adx_min
            rsi_ok = rsi_val > self.rsi_threshold
            macd_ok = macd_val > macds_val
            vol_ratio = vol / vol_avg
            vol_ok = vol_ratio > self.volume_multiplier
            ema_ok = curr_price > ema_100
            is_met = adx_ok and rsi_ok and macd_ok and vol_ok and ema_ok
            triggers.append(("🔹 코어 브레이크아웃", bool(is_met)))
            triggers.append((f"    ADX>{self.breakout_adx_min}: 현재 {adx_val:.1f}", bool(adx_ok)))
            triggers.append((f"    RSI>{self.rsi_threshold}: 현재 {rsi_val:.1f}", bool(rsi_ok)))
            triggers.append((f"    MACD>시그널: {macd_val:.1f}/{macds_val:.1f}", bool(macd_ok)))
            triggers.append((f"    거래량>{self.volume_multiplier}x: 현재 {vol_ratio:.1f}x", bool(vol_ok)))
            triggers.append((f"    가격>EMA100: {curr_price:,.0f} vs {ema_100:,.0f}", bool(ema_ok)))

        # 신호 2: TREND RIDER
        prev_ema20 = _val(prev, 'EMA_20')
        prev_close = _val(prev, 'close')
        if all(v is not None for v in (adx_val, rsi_val, ema_20, prev_ema20, prev_close)):
            adx_ok = adx_val > self.trend_rider_adx_min
            bounce_ok = prev_close < prev_ema20 and curr_price > ema_20
            rsi_ok = rsi_val > self.trend_rider_rsi_min
            is_met = adx_ok and bounce_ok and rsi_ok
            triggers.append(("🔹 트렌드 라이더", bool(is_met)))
            triggers.append((f"    ADX>{self.trend_rider_adx_min}: 현재 {adx_val:.1f}", bool(adx_ok)))
            triggers.append((f"    EMA20 반등: 이전종가{'<' if prev_close < prev_ema20 else '≥'}EMA20, 현재가{'>' if curr_price > ema_20 else '≤'}EMA20", bool(bounce_ok)))
            triggers.append((f"    RSI>{self.trend_rider_rsi_min}: 현재 {rsi_val:.1f}", bool(rsi_ok)))

        # 신호 3: BULL PULLBACK
        prev_low = _val(prev, 'low')
        if all(v is not None for v in (ema_50, rsi_val, macd_val, macds_val, vol, vol_avg, prev_low)) and vol_avg > 0:
            bounce_ok = prev_low < ema_50 and curr_price > ema_50
            rsi_ok = rsi_val > self.pullback_rsi_min
            macd_ok = macd_val > macds_val
            vol_ratio = vol / vol_avg
            vol_ok = vol_ratio > self.pullback_volume_multiplier
            is_met = bounce_ok and rsi_ok and macd_ok and vol_ok
            triggers.append(("🔹 불 풀백", bool(is_met)))
            triggers.append((f"    EMA50 반등: 이전저가{'<' if prev_low < ema_50 else '≥'}EMA50, 현재가{'>' if curr_price > ema_50 else '≤'}EMA50", bool(bounce_ok)))
            triggers.append((f"    RSI>{self.pullback_rsi_min}: 현재 {rsi_val:.1f}", bool(rsi_ok)))
            triggers.append((f"    MACD>시그널: {macd_val:.1f}/{macds_val:.1f}", bool(macd_ok)))
            triggers.append((f"    거래량>{self.pullback_volume_multiplier}x: 현재 {vol_ratio:.1f}x", bool(vol_ok)))

        return triggers

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int) -> float:
        adx = df.iloc[current_idx].get(self.adx_col, 0)
        if adx is None or pd.isna(adx):
            return 1.0
        if adx > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return self.risk_default_multiplier
