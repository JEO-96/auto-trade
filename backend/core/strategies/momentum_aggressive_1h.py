"""
MomentumAggressive1hStrategy - 1시간봉 전용 공격적 모멘텀 전략.

공격형 전략답게 진입 기회를 넓히고 큰 수익을 노림:
- RSI 55 (낮은 임계값으로 더 많은 진입 기회)
- ADX 20 (추세 초기 단계에서 진입)
- 볼륨 1.5x (1h 볼륨 노이즈 보정)
- EMA_200 매크로 필터만 사용 (EMA_20/50 정렬 제거 — 더 공격적)
- ATR SL 1.5x, TP 4.0x (1:4 RR), trailing 2.5x (큰 수익 추구)
- 리스크 스케일링: ADX > 35일 때 2.0x (공격적 포지션 확대)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumAggressive1hStrategy(BaseStrategy):
    """
    1시간봉 전용 공격적 모멘텀 브레이크아웃 전략.

    Basic 대비 공격적 변경점:
    - 낮은 RSI/ADX 임계값으로 더 많은 진입 기회
    - EMA_20 > EMA_50 정렬 조건 제거 (진입 제약 완화)
    - 높은 TP 배수(4.0x)로 큰 수익 추구
    - 넓은 trailing stop(2.5x)으로 수익 극대화
    - 높은 리스크 스케일링 (2.0x)
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 공격적 신호 임계값 (낮은 진입 장벽)
        self.rsi_threshold = 55
        self.adx_threshold = 20
        self.volume_multiplier = 1.5

        # 공격적 출구 파라미터 (큰 수익 추구, 1:4 RR)
        self.atr_sl_multiplier = 1.5
        self.atr_tp_multiplier = 4.0
        self.trailing_stop_multiplier = 2.5

        # 백테스트 SL/TP (그리드 서치 최적화: 125% PnL, 37.1% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.15   # 15% TP

        # 풀백 ADX 임계값 (더 많은 풀백 진입)
        self.pullback_adx_threshold = 25

        # 리스크 스케일링 (공격적)
        self.risk_adx_threshold = 35
        self.risk_high_multiplier = 2.0

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        # 필수 지표 NaN 검증
        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col,
            'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 매크로 추세 필터: 가격 > EMA_200 (유일한 EMA 필터)
        if current['close'] < current['EMA_200']:
            return False

        # EMA_20 > EMA_50 정렬 필터 제거 — 공격적 전략은 진입 제약 최소화

        # 브레이크아웃 조건 (공격적: 낮은 임계값으로 진입 기회 확대)
        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # 풀백 진입 조건
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and current['close'] > current['EMA_50']
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
            )

        return breakout or pullback

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

        # 신호 1: 브레이크아웃
        rsi = _val(current, self.rsi_col)
        adx = _val(current, self.adx_col)
        macd = _val(current, self.macd_col)
        macds = _val(current, self.macds_col)
        vol = _val(current, 'volume')
        vol_ma = _val(current, self.vol_ma_col)
        if all(v is not None for v in (rsi, adx, macd, macds, vol, vol_ma)) and vol_ma > 0:
            rsi_ok = rsi > self.rsi_threshold
            adx_ok = adx > self.adx_threshold
            macd_ok = macd > macds
            vol_ratio = vol / vol_ma
            vol_ok = vol_ratio > self.volume_multiplier
            is_met = rsi_ok and adx_ok and macd_ok and vol_ok
            triggers.append(("🔹 브레이크아웃", bool(is_met)))
            triggers.append((f"    RSI>{self.rsi_threshold}: 현재 {rsi:.1f}", bool(rsi_ok)))
            triggers.append((f"    ADX>{self.adx_threshold}: 현재 {adx:.1f}", bool(adx_ok)))
            triggers.append((f"    MACD>시그널: {macd:.1f}/{macds:.1f}", bool(macd_ok)))
            triggers.append((f"    거래량>{self.volume_multiplier}x: 현재 {vol_ratio:.1f}x", bool(vol_ok)))

        # 신호 2: 풀백 진입
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        ema50 = _val(current, 'EMA_50')
        prev_close = _val(prev, 'close')
        if all(v is not None for v in (adx, ema50, prev_ema20, prev_close, curr_ema20)):
            adx_ok = adx > self.pullback_adx_threshold
            price_gt_ema50 = curr_price > ema50
            bounce_ok = prev_close < prev_ema20 and curr_price > curr_ema20
            is_met = adx_ok and price_gt_ema50 and bounce_ok
            triggers.append(("🔹 풀백 진입", bool(is_met)))
            triggers.append((f"    ADX>{self.pullback_adx_threshold}: 현재 {adx:.1f}", bool(adx_ok)))
            triggers.append((f"    가격>EMA50: {curr_price:,.0f} vs {ema50:,.0f}", bool(price_gt_ema50)))
            triggers.append((f"    EMA20 반등: 이전종가{'<' if prev_close < prev_ema20 else '≥'}EMA20, 현재가{'>' if curr_price > curr_ema20 else '≤'}EMA20", bool(bounce_ok)))

        return triggers

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int) -> float:
        """공격적 리스크 스케일링: ADX > 35일 때 2.0x 포지션 확대."""
        adx_val = df.iloc[current_idx].get(self.adx_col, 0)
        if pd.isna(adx_val):
            return 1.0
        if adx_val > self.risk_adx_threshold:
            return self.risk_high_multiplier
        return 1.0
