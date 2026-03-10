import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class SteadyCompounderStrategy(BaseStrategy):
    """
    Steady Compounder - 주간 1~2% 목표의 고승률 스윙 전략

    핵심 철학: 큰 추세를 잡지 않고, 작은 수익을 자주 확정한다.
    - RSI 과매도 반등 (눌림목 매수)
    - MACD 골든크로스 확인
    - EMA 정배열 추세 확인
    - 짧은 익절 (ATR 1.5배) + 타이트 손절 (ATR 1.0배)
    - 트레일링 스탑으로 수익 보호

    목표: 승률 60%+, 평균 익절 1.5~2%, 평균 손절 1%
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # RSI 눌림목 진입 구간
        self.rsi_entry_low = 35       # RSI가 이 밑으로 내려갔다가
        self.rsi_entry_high = 50      # 이 위로 올라오면 반등 신호
        self.rsi_max = 65             # 이 이상이면 이미 올라간 것, 패스

        # ADX 최소 추세 강도 (너무 약한 횡보장 제외)
        self.adx_min = 15

        # 거래량 필터 (평균 대비 배수, 낮게 설정 → 신호 빈도 높임)
        self.volume_multiplier = 1.2

        # 손익 파라미터 (빠른 익절, 타이트 손절)
        self.atr_sl_multiplier = 1.0     # 손절: ATR 1.0배
        self.atr_tp_multiplier = 1.5     # 익절: 리스크의 1.5배 (1:1.5 RR)
        self.trailing_stop_multiplier = 1.2  # 트레일링: ATR 1.2배 (빠르게 수익 확정)

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        adx_col = "ADX_14"

        # 필수 지표 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, adx_col, 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        rsi_curr = current[self.rsi_col]
        rsi_prev = prev.get(self.rsi_col)
        if rsi_prev is None or pd.isna(rsi_prev):
            return False

        # ─── 조건 1: RSI 눌림목 반등 ───
        # 이전 캔들이 과매도 구간 근처, 현재 캔들이 회복 중
        rsi_bounce = (
            rsi_prev < self.rsi_entry_high and
            rsi_curr > rsi_prev and
            rsi_curr < self.rsi_max
        )
        if not rsi_bounce:
            return False

        # ─── 조건 2: MACD 시그널 위 (상승 모멘텀) ───
        if current[self.macd_col] <= current[self.macds_col]:
            return False

        # ─── 조건 3: EMA 정배열 (20 > 50 = 단기 상승 추세) ───
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # ─── 조건 4: 가격이 EMA_20 위 (추세 안에 있음) ───
        if current['close'] < current['EMA_20']:
            return False

        # ─── 조건 5: 최소 추세 강도 확인 ───
        if current[adx_col] < self.adx_min:
            return False

        # ─── 조건 6: 거래량 활성화 확인 ───
        if current['volume'] < current[self.vol_ma_col] * self.volume_multiplier:
            return False

        return True

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)

        # 타이트 손절 (ATR 1.0배)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)

        # 빠른 익절 (리스크의 1.5배)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)

        return stop_loss, take_profit
