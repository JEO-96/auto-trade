"""
Momentum Elite 1d - 일봉 전용 엘리트 전략

기존 momentum_breakout_elite의 1d 타임프레임 최적화 버전.
기준선: +43.45% / 237 trades / 42.6% win / 56.9% MaxDD
- 수익률은 양호하나 MaxDD 56.9%와 과다 거래(237건)가 문제
- 3개 시그널 유지하되 진입 문턱 강화
- RSI 55, Volume 1.5x, ADX 차등 적용
- Bull Pullback: RSI > 50 + MACD > signal 조건 추가
- close > EMA_200 모든 시그널 필수
- ATR SL 2.0x, TP 5.0x (1:5 RR), trailing 2.5x
"""
import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumElite1dStrategy(BaseStrategy):
    """
    일봉 전용 Momentum Elite 전략.

    1d 타임프레임에서 +43.45% 수익을 기록했으나 56.9% MaxDD와
    237건의 과다 거래가 문제였습니다. 모든 시그널에 EMA_200 위
    조건을 필수로 부과하고, Bull Pullback에 MACD 필터를 추가하여
    거래 횟수와 드로다운을 줄입니다.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 인디케이터 파라미터
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.volume_ma_period = 20

        # 시그널 임계값 — 1d 최적화
        self.rsi_threshold = 55
        self.volume_multiplier = 1.5

        # ADX 차등 문턱
        self.breakout_adx_min = 22
        self.trend_rider_adx_min = 28
        self.trend_rider_rsi_min = 52

        # Bull Pullback — 강화된 조건
        self.pullback_rsi_min = 50

        # 출구 파라미터 — 넓은 SL, 1:5 RR
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 5.0
        self.trailing_stop_multiplier = 2.5

        # 리스크 스케일링
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 2.0
        self.risk_default_multiplier = 1.2

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """표준 인디케이터 + EMA_100 추가."""
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

        # NaN 가드
        core_vals = [rsi_val, adx_val, macd_val, macds_val, vol_avg, ema_200, ema_100, ema_50, ema_20]
        if any(v is None or pd.isna(v) for v in core_vals):
            return False
        if vol_avg == 0:
            return False

        # 모든 시그널 필수 조건: close > EMA_200
        if current['close'] <= ema_200:
            return False

        # 1. CORE BREAKOUT: RSI + MACD + Volume + EMA_100 + ADX
        breakout = (
            adx_val > self.breakout_adx_min
            and rsi_val > self.rsi_threshold
            and macd_val > macds_val
            and current['volume'] > vol_avg * self.volume_multiplier
            and current['close'] > ema_100
        )

        # 2. TREND RIDER: 강한 추세 진입
        trend_rider = False
        if not any(v is None or pd.isna(v) for v in [dmp_val, dmn_val]):
            prev_ema20 = prev.get('EMA_20', None)
            if prev_ema20 is not None and not pd.isna(prev_ema20):
                trend_rider = (
                    adx_val > self.trend_rider_adx_min
                    and dmp_val > dmn_val
                    and current['close'] > ema_20
                    and prev['close'] < prev_ema20
                    and rsi_val > self.trend_rider_rsi_min
                )

        # 3. BULL PULLBACK: EMA 터치 + RSI 50 이상 + MACD 필터
        bull_pullback = (
            prev['low'] < ema_50
            and current['close'] > ema_50
            and rsi_val > self.pullback_rsi_min
            and macd_val > macds_val
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
        """ADX > 35일 때 리스크 증가."""
        adx = df.iloc[current_idx].get(self.adx_col, 0)
        if adx is None or pd.isna(adx):
            return 1.0
        if adx > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return self.risk_default_multiplier
