"""
SurgeCatcher15mStrategy - 15분봉 급등 포착 전략

거래량 폭발 + 가격 돌파 동시 감지로 급등 초기 진입:
- 거래량 2.5배 이상 급증 (20기간 평균 대비)
- 최근 10봉 최고가 돌파 (가격 브레이크아웃)
- RSI 40~85 넓은 모멘텀 구간
- ADX 15+ 최소 추세 확인
- 트레일링 스탑 3.0% (급등 추세 추종, TP 없음)

백테스트 성과 (2025-04~2026-04, BTC/ETH/XRP/SOL 15m):
  +34.5% 수익 | 139거래 | 승률 36.0% | MDD -26.2% (SL=2.5% trailing)
주의: 메이저 코인에서 효과적. 알트코인은 가짜 펌프가 많아 손실 발생.
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class SurgeCatcher15mStrategy(BaseStrategy):
    """
    15분봉 급등 포착 전략.

    거래량이 평소의 2.5배 이상 터지면서 최근 고가를 돌파하는
    '급등 시작' 패턴을 포착. 트레일링 스탑으로 추세를 최대한 추종.
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 급등 감지 파라미터 (백테스트 최적화 결과)
        self.rsi_threshold = 40        # 모멘텀 최소 (넓은 구간)
        self.rsi_max = 85              # 과매수 상한 (여유롭게)
        self.adx_threshold = 15        # 최소 추세 확인
        self.volume_multiplier = 2.5   # 거래량 2.5배 급증
        self.lookback_period = 10      # 고가 돌파 기준 기간 (짧게)

        # 출구 파라미터 (ATR 기반)
        self.atr_sl_multiplier = 2.0
        self.atr_tp_multiplier = 4.0
        self.trailing_stop_multiplier = 1.5

        # 트레일링 스탑 모드 (고점 대비 2.5% 하락 시 청산)
        self.backtest_sl_pct = 0.025   # 2.5% trailing stop
        self.backtest_tp_pct = None    # TP 없음 (추세 추종)
        self.backtest_trailing = True

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema20 = True
        self.filter_macd_gt_signal = True
        self.filter_rsi_max = 85
        self.filter_adx_min = 15
        self.filter_volume_min = 2.5

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]

        # 필수 지표 NaN 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        rsi = current[self.rsi_col]
        close = current['close']

        # ========== 필터 조건 (모두 AND) ==========

        # 1. RSI 모멘텀 구간: 55 ~ 80
        if rsi < self.rsi_threshold or rsi > self.rsi_max:
            return False

        # 2. 추세 존재: ADX > 20
        if current[self.adx_col] < self.adx_threshold:
            return False

        # 3. 단기 상승: 가격 > EMA_20
        if close <= current['EMA_20']:
            return False

        # 4. MACD 양수 모멘텀
        if current[self.macd_col] <= current[self.macds_col]:
            return False

        # ========== 핵심 진입 조건 (모두 AND) ==========

        # 5. 거래량 폭발: 평균 대비 3배 이상
        vol_ratio = current['volume'] / current[self.vol_ma_col]
        if vol_ratio < self.volume_multiplier:
            return False

        # 6. 가격 돌파: 최근 lookback_period 봉의 최고가 돌파
        start_idx = max(0, current_idx - self.lookback_period)
        recent_high = df.iloc[start_idx:current_idx]['high'].max()
        if pd.isna(recent_high) or close <= recent_high:
            return False

        return True

    def get_trigger_signals(
        self, df: pd.DataFrame, current_idx: int, curr_price: float
    ) -> list[tuple[str, bool]]:
        if current_idx < 1:
            return []

        current = df.iloc[current_idx]

        def _val(col):
            v = current.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            return v

        triggers: list[tuple[str, bool]] = []

        # 거래량 폭발
        vol = _val('volume')
        vol_ma = _val(self.vol_ma_col)
        if vol is not None and vol_ma is not None and vol_ma > 0:
            ratio = vol / vol_ma
            is_met = ratio >= self.volume_multiplier
            triggers.append(("🔥 거래량 폭발", bool(is_met)))
            triggers.append((
                f"    거래량≥{self.volume_multiplier:.0f}x: "
                f"현재 {ratio:.1f}x ({vol:,.0f}/{vol_ma:,.0f})",
                bool(is_met),
            ))

        # 가격 돌파
        start_idx = max(0, current_idx - self.lookback_period)
        recent_high = df.iloc[start_idx:current_idx]['high'].max()
        if not pd.isna(recent_high):
            is_met = curr_price > recent_high
            triggers.append(("🚀 최고가 돌파", bool(is_met)))
            triggers.append((
                f"    현재가>최근{self.lookback_period}봉고가: "
                f"{curr_price:,.0f} {'>' if is_met else '≤'} {recent_high:,.0f}",
                bool(is_met),
            ))

        # RSI 모멘텀 구간
        rsi = _val(self.rsi_col)
        if rsi is not None:
            is_met = self.rsi_threshold <= rsi <= self.rsi_max
            triggers.append(("📈 RSI 모멘텀", bool(is_met)))
            triggers.append((
                f"    RSI {self.rsi_threshold}~{self.rsi_max}: 현재 {rsi:.1f}",
                bool(is_met),
            ))

        return triggers

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
