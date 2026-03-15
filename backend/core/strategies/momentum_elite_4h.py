"""
MomentumElite4hStrategy - 4시간봉 전용 엘리트 전략

v2 변경사항 (필터 강화 + 임계값 완화):
- 골든크로스 필터: EMA_50 > EMA_200 (전 시그널 공통)
- DI+ > DI- 방향성 필터 (전 시그널 공통)
- RSI 상한 77 (과매수 진입 방지)
- breakout_adx_min 24→22 (확인된 추세에서 더 많은 진입)
- trend_rider_adx_min 30→26 (확인된 추세에서 더 많은 추세추종)
- ATR TP 4.0→4.5 (엘리트는 더 큰 수익 목표)
- Bull Pullback 볼륨 필터 추가: volume > vol_avg * 1.2
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumElite4hStrategy(BaseStrategy):
    """4시간봉 전용 Momentum Elite 전략."""

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
        self.rsi_upper_limit = 77  # 과매수 진입 방지
        self.volume_multiplier = 1.5
        self.pullback_volume_multiplier = 1.2  # Bull Pullback 볼륨 필터

        # ADX 차등 문턱 (골든크로스+DI 필터로 낮춰도 안전)
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

        # 백테스트 SL/TP (그리드 서치 최적화: 97% PnL, 16.4% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.10   # 10% TP

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

        # === 공통 필터 (전 시그널 적용) ===
        # 가격 > EMA_200
        if current['close'] <= ema_200:
            return False
        # 골든크로스: EMA_50 > EMA_200
        if ema_50 <= ema_200:
            return False
        # 방향성 필터: DI+ > DI-
        if dmp_val <= dmn_val:
            return False
        # 과매수 진입 방지
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

        # 3. BULL PULLBACK (볼륨 필터 추가)
        bull_pullback = (
            prev['low'] < ema_50
            and current['close'] > ema_50
            and rsi_val > self.pullback_rsi_min
            and macd_val > macds_val
            and current['volume'] > vol_avg * self.pullback_volume_multiplier
        )

        return breakout or trend_rider or bull_pullback

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
