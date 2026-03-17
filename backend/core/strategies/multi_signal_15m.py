"""
MultiSignal15mStrategy - 15분봉 멀티시그널 전략

3가지 진입 경로 (돌파/추세/풀백):
- Golden Cross + DI+ 방향성 글로벌 필터
- 돌파: ADX 25+, RSI 55+, MACD, 볼륨 1.3x
- 추세: ADX 30+, EMA_20 바운스, RSI 50+
- 풀백: EMA_50 반등 + MACD + RSI 50+
- 트레일링 스탑 2.0%
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MultiSignal15mStrategy(BaseStrategy):
    """15분봉 멀티시그널 전략 (돌파/추세/풀백 3중 신호)."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 시그널 임계값 (멀티심볼 최적화: rsi 50, vol 1.2x)
        self.rsi_threshold = 50
        self.volume_multiplier = 1.2

        # ADX 차등 문턱 (멀티심볼 최적화: 높은 ADX로 노이즈 필터)
        self.breakout_adx_min = 28
        self.trend_rider_adx_min = 35
        self.trend_rider_rsi_min = 50

        # Bull Pullback
        self.pullback_rsi_min = 50
        self.pullback_volume_multiplier = 1.1

        # RSI 과매수 상한
        self.rsi_upper_limit = 76

        # 출구 파라미터 (실매매용 ATR 기반)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 3.0
        self.trailing_stop_multiplier = 2.0

        # 트레일링 스탑 모드 (멀티심볼 최적화: TRAIL 2.0%가 최적)
        self.backtest_sl_pct = 0.020   # 2.0% trailing stop
        self.backtest_tp_pct = None    # TP 없음
        self.backtest_trailing = True

        # 리스크 스케일링
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 1.5

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

        core_vals = [rsi_val, adx_val, macd_val, macds_val, vol_avg, ema_200, ema_50, ema_20]
        if any(v is None or pd.isna(v) for v in core_vals):
            return False
        if vol_avg == 0:
            return False

        # 가격 > EMA_200
        if current['close'] <= ema_200:
            return False

        # Golden Cross: EMA_50 > EMA_200
        if ema_50 <= ema_200:
            return False

        # DI+ > DI-
        if dmp_val is None or dmn_val is None or pd.isna(dmp_val) or pd.isna(dmn_val):
            return False
        if dmp_val <= dmn_val:
            return False

        # RSI 과매수 상한
        if rsi_val > self.rsi_upper_limit:
            return False

        # 1. CORE BREAKOUT
        breakout = (
            adx_val > self.breakout_adx_min
            and rsi_val > self.rsi_threshold
            and macd_val > macds_val
            and current['volume'] > vol_avg * self.volume_multiplier
        )
        # EMA_100 필터 (있으면 적용)
        if breakout and ema_100 is not None and not pd.isna(ema_100):
            breakout = current['close'] > ema_100

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

        # 3. BULL PULLBACK
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
        return 1.0
