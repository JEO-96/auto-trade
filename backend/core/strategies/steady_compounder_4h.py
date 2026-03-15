import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class SteadyCompounder4hStrategy(BaseStrategy):
    """
    Steady Compounder 4h - 4시간봉 최적화 전략

    기존 Steady Compounder 4h 성과: +20.98%, 50% 승률, 9.4% MaxDD
    이미 최고의 리스크 조정 수익률을 보여주는 타임프레임.

    미세 조정 내용 (기존 로직 유지 + 소폭 개선):
    - 3번째 진입 신호 추가: EMA_20 바운스 (가격이 EMA_20 아래에서 위로 돌파)
    - 익절 ATR 3.0x -> 3.5x로 소폭 상향 (수익 구간 확대)
    - ADX > 15 가벼운 필터 추가 (횡보장 거짓 신호 감소)
    - RSI 과열 기준 75 유지 (변경 없음)
    - 손절/트레일링 기존과 동일
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 4h 손익 파라미터 (소폭 조정)
        self.atr_sl_multiplier = 1.5      # 손절: ATR 1.5배 (유지)
        self.atr_tp_multiplier = 3.5      # 익절: 리스크의 3.5배 (기존 3.0 -> 3.5)
        self.trailing_stop_multiplier = 2.0  # 트레일링: ATR 2.0배 (유지)

        # 트레일링 스탑 모드: 고점 대비 5% 하락 시 청산, TP 없음 (추세 추종)
        self.backtest_sl_pct = 0.05   # 고점 대비 5% 트레일링 스탑
        self.backtest_tp_pct = None   # TP 없음
        self.backtest_trailing = True  # 트레일링 모드 활성화

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

        # ========== 공통 필터 (반드시 통과해야 함) ==========

        # 1. EMA 정배열: EMA_20 > EMA_50 (상승 추세)
        if current['EMA_20'] <= current['EMA_50']:
            return False

        # 2. 가격이 EMA_20 위 (추세 안에 있음)
        if current['close'] < current['EMA_20']:
            return False

        # 3. MACD가 시그널 위 (상승 모멘텀)
        if macd_val <= macds_val:
            return False

        # 4. RSI 과열 아님 (75 유지)
        if rsi_curr > 75:
            return False

        # 5. ADX > 15 (가벼운 추세 필터, 횡보장 제외)
        if current[self.adx_col] < 15:
            return False

        # 6. 거래량 평균 이상
        if current['volume'] < current[self.vol_ma_col]:
            return False

        # ========== 진입 신호 (하나만 충족하면 됨) ==========

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

        # 신호 3: EMA_20 바운스 (가격이 EMA_20 아래에서 위로 복귀)
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

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)

        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)

        return stop_loss, take_profit
