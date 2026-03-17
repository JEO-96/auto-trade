"""
SignalTest15mStrategy - 15분봉 매매 테스트 전략

매매 실행 확인 전용 (성능 무관):
- 조건: 가격 > 0 이면 무조건 매수 (거의 매 봉 진입)
- 고정 SL 0.5% / TP 0.5% (빠른 청산으로 회전율 극대화)
- 실제 수익 목적이 아닌, 봇 매매 동작 검증용
"""

import pandas as pd
from core.strategies.base import BaseStrategy


class SignalTest15mStrategy(BaseStrategy):
    """15분봉 매매 테스트 전략 (매 봉 진입 시도, 빠른 청산)."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = False

        # 출구: 극히 좁은 SL/TP로 빠른 회전
        self.atr_sl_multiplier = 0.5
        self.atr_tp_multiplier = 0.5

        # 백테스트/실매매 공통: 0.5% SL, 0.5% TP
        self.backtest_sl_pct = 0.005
        self.backtest_tp_pct = 0.005
        self.backtest_trailing = False

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]

        # 최소한의 유효성만 확인 (가격과 RSI가 존재하는지)
        close = current.get('close', None)
        rsi = current.get(self.rsi_col, None)
        if close is None or rsi is None:
            return False
        if pd.isna(close) or pd.isna(rsi):
            return False

        # 거의 항상 True — RSI가 존재하면 매수
        return True

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        take_profit = entry_price + (atr * self.atr_tp_multiplier)
        return stop_loss, take_profit
