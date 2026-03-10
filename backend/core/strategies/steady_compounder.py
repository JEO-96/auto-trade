import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class SteadyCompounderStrategy(BaseStrategy):
    """
    Steady Compounder - 주간 1~2% 목표의 고승률 스윙 전략

    핵심 철학: 확실한 추세 안에서만 진입, 빠르게 수익 확정.
    - EMA 정배열 + MACD 상승 = 추세 확인
    - 거래량 확인으로 신호 품질 향상
    - 2가지 진입 신호 (OR): RSI 반등 / MACD 골든크로스
    - 넉넉한 익절 (ATR 3.0배) + 적당한 손절 (ATR 1.5배)
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 손익 파라미터
        self.atr_sl_multiplier = 1.5     # 손절: ATR 1.5배
        self.atr_tp_multiplier = 3.0     # 익절: 리스크의 3.0배 (1:3 RR)
        self.trailing_stop_multiplier = 2.0  # 트레일링: ATR 2.0배

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, 'EMA_50', 'EMA_20',
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

        # ═══ 공통 필터 (반드시 통과해야 함) ═══

        # 1. EMA 정배열: EMA_20 > EMA_50 (상승 추세)
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 2. 가격이 EMA_20 위 (추세 안에 있음)
        if current['close'] < current['EMA_20']:
            return False

        # 3. MACD가 시그널 위 (상승 모멘텀)
        if macd_val <= macds_val:
            return False

        # 4. RSI 과열 아님
        if rsi_curr > 75:
            return False

        # 5. 거래량 평균 이상 (관심 있는 움직임만)
        if current['volume'] < current[self.vol_ma_col]:
            return False

        # ═══ 진입 신호 (하나만 충족하면 됨) ═══

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

        return signal_rsi_bounce or signal_macd_cross

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)

        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)

        return stop_loss, take_profit
