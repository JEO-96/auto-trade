"""
MomentumStable1dStrategy - 일봉 최적화 모멘텀 안정형 전략

트레일링 스탑 추세 추종 모드:
- RSI 50, ADX 18, 볼륨 1.0x (일봉 신호 적극 포착)
- DI+ > DI- 방향성 필터
- EMA_50 > EMA_200 골든크로스 필터
- 최근 2봉 최고 종가 돌파 조건
- 트레일링 스탑 5% (고점 대비 하락 시 청산, TP 없음)
"""
import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable1dStrategy(BaseStrategy):
    """
    일봉 최적화 모멘텀 안정형 전략.

    일봉은 노이즈가 적지만 추세 형성이 느리므로,
    골든크로스 + 신고가 돌파 + DI+ 방향성 확인으로 강한 상승 추세만 진입.
    타이트한 손절/익절로 낮은 MaxDD 유지 (안정형 핵심 목표).
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 신호 임계값 (완화: 일봉 신호 적극 포착)
        self.rsi_threshold = 50
        self.rsi_upper_limit = 78
        self.adx_threshold = 18
        self.volume_multiplier = 1.0

        # 출구 파라미터 (실매매용 ATR 기반)
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.5

        # 백테스트/실매매: 트레일링 스탑 모드 (고점 대비 5% 하락 시 청산)
        self.backtest_sl_pct = 0.05   # 5% trailing stop
        self.backtest_tp_pct = None   # TP 없음 (추세 추종)
        self.backtest_trailing = True

        # 풀백 ADX 임계값
        self.pullback_adx_threshold = 15

        # 최근 N봉 최고가 돌파 조건
        self.breakout_lookback = 2

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema50_gt_ema200 = True
        self.filter_di_positive = True
        self.filter_rsi_max = 78

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col,
            'EMA_200', 'EMA_50', 'EMA_20',
            self.dmp_col, self.dmn_col,
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 추세 필터 1: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 추세 필터 2: 골든크로스 (EMA_50 > EMA_200)
        if current['EMA_50'] <= current['EMA_200']:
            return False

        # 방향성 필터: DI+ > DI- (상승 추세 확인)
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # 과매수 방지: RSI 상한
        if current[self.rsi_col] > self.rsi_upper_limit:
            return False

        # 최근 N봉 최고 종가 돌파 확인
        lookback_start = max(0, current_idx - self.breakout_lookback)
        recent_closes = df.iloc[lookback_start:current_idx]['close']
        if len(recent_closes) == 0:
            return False
        highest_recent_close = recent_closes.max()

        # 브레이크아웃 신호 (위크 필터 없음 + 신고가 돌파)
        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
            and current['close'] > highest_recent_close
        )

        # 풀백 신호 (골든크로스 환경에서만)
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
            )

        return breakout or pullback

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
