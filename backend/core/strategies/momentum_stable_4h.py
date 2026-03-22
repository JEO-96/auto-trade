"""
MomentumStable4hStrategy - 4시간봉 최적화 모멘텀 안정형 전략

MaxDD 최소화 목표 (basic_4h 14.0% 이하 → 목표 <14%):
- RSI 임계값 53, RSI < 74 과매수 필터 (강화)
- ADX 임계값 22 (강화: 19→22)
- DI+ > DI- 방향성 필터 추가
- 볼륨 배수 1.5x
- ATR SL 1.2x, TP 2.5x, trailing 1.5x (타이트한 손절/익절)
- 골든크로스 필터 (EMA_50 > EMA_200)
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumStable4hStrategy(BaseStrategy):
    """4시간봉 최적화 모멘텀 안정형 전략."""

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 4h 신호 임계값
        self.rsi_threshold = 53
        self.rsi_overbought = 76
        self.adx_threshold = 19
        self.volume_multiplier = 1.5

        # 4h 출구 파라미터
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.0

        # 백테스트 SL/TP (그리드 서치 최적화: 94% PnL, 34.3% MaxDD)
        self.backtest_sl_pct = 0.015  # 1.5% SL
        self.backtest_tp_pct = 0.25   # 25% TP

        # 풀백 ADX
        self.pullback_adx_threshold = 26

        # 위크 필터
        self.wick_filter_ratio = 0.9

        # 텔레그램 체크리스트 필터
        self.filter_close_gt_ema200 = True
        self.filter_ema50_gt_ema200 = True
        self.filter_rsi_max = 76

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 200:
            return False

        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]

        required_cols = [
            self.rsi_col, self.macd_col, self.macds_col,
            self.vol_ma_col, self.adx_col, 'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 추세 필터: 가격 > EMA_200
        if current['close'] < current['EMA_200']:
            return False

        # 골든크로스 필터: EMA_50 > EMA_200
        if current['EMA_50'] <= current['EMA_200']:
            return False

        # RSI 과매수 가드
        if current[self.rsi_col] > self.rsi_overbought:
            return False

        # 브레이크아웃 신호
        breakout = (
            current[self.rsi_col] > self.rsi_threshold
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # 풀백 신호
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
            )

        if breakout or pullback:
            body = abs(current['close'] - current['open'])
            wick = current['high'] - max(current['close'], current['open'])
            if body > 0 and wick > body * self.wick_filter_ratio:
                return False
            return True

        return False

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
        prev_close = _val(prev, 'close')
        if all(v is not None for v in (adx, prev_ema20, prev_close, curr_ema20)):
            adx_ok = adx > self.pullback_adx_threshold
            bounce_ok = prev_close < prev_ema20 and curr_price > curr_ema20
            is_met = adx_ok and bounce_ok
            triggers.append(("🔹 풀백 진입", bool(is_met)))
            triggers.append((f"    ADX>{self.pullback_adx_threshold}: 현재 {adx:.1f}", bool(adx_ok)))
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
