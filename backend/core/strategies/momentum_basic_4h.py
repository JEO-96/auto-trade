"""
MomentumBasic4hStrategy - 4시간봉 최적화 모멘텀 기본 전략

momentum_basic_1d 대비 변경:
- RSI 임계값 60 (4h 중간 수준)
- 볼륨 배수 1.8x
- ADX 임계값 23
- ATR SL 1.8x, TP 3.5x (중간 폭)
- 트레일링 2.0x ATR
"""

import pandas as pd
import numpy as np
from core.strategies.base import BaseStrategy


class MomentumBasic4hStrategy(BaseStrategy):
    """4시간봉 최적화 모멘텀 기본 전략."""

    def __init__(self) -> None:
        super().__init__()
        self.use_trailing_stop = True

        # 4h 최적화 신호 임계값
        self.rsi_threshold = 60.0
        self.adx_threshold = 23.0
        self.volume_multiplier = 1.8

        # 4h 출구 파라미터 (중간)
        self.atr_sl_multiplier = 1.8
        self.atr_tp_multiplier = 3.5
        self.trailing_stop_multiplier = 2.0

        # 백테스트 SL/TP (그리드 서치 최적화: 122% PnL, 18.4% MaxDD)
        self.backtest_sl_pct = 0.02   # 2% SL
        self.backtest_tp_pct = 0.25   # 25% TP

        # 풀백 진입용 ADX
        self.pullback_adx_threshold = 28

        # 위크 필터
        self.wick_filter_ratio = 0.9

        # RSI 과열 상한
        self.rsi_upper_limit = 78.0

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
            self.vol_ma_col, self.adx_col, self.dmp_col, self.dmn_col,
            'EMA_200', 'EMA_50', 'EMA_20',
        ]
        if not self._validate_indicators(current, required_cols):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        # 이중 트렌드 필터
        if current['close'] < current['EMA_200']:
            return False
        if current['EMA_50'] < current['EMA_200']:
            return False

        # 방향성 필터
        if current[self.dmp_col] <= current[self.dmn_col]:
            return False

        # RSI 과열 방지
        rsi_curr = current[self.rsi_col]
        if rsi_curr > self.rsi_upper_limit:
            return False

        rsi_prev = prev.get(self.rsi_col)
        if rsi_prev is None or pd.isna(rsi_prev):
            return False

        # 신호 1: 모멘텀 브레이크아웃
        rsi_cross_up = (rsi_prev <= self.rsi_threshold) and (rsi_curr > self.rsi_threshold)
        rsi_momentum = rsi_curr - rsi_prev > 5

        breakout = (
            (rsi_cross_up or (rsi_curr > self.rsi_threshold and rsi_momentum))
            and current[self.adx_col] > self.adx_threshold
            and current[self.macd_col] > current[self.macds_col]
            and current['volume'] > current[self.vol_ma_col] * self.volume_multiplier
        )

        # 신호 2: 풀백 진입
        prev_ema20 = prev.get('EMA_20')
        pullback = False
        if not pd.isna(prev_ema20):
            pullback = (
                current[self.adx_col] > self.pullback_adx_threshold
                and prev['close'] < prev_ema20
                and current['close'] > current['EMA_20']
                and current[self.macd_col] > current[self.macds_col]
                and current['volume'] > current[self.vol_ma_col]
            )

        if not (breakout or pullback):
            return False

        # 위크 필터
        body = abs(current['close'] - current['open'])
        wick = current['high'] - max(current['close'], current['open'])
        if body > 0 and wick > body * self.wick_filter_ratio:
            return False

        return True

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

        # 신호 1: 모멘텀 브레이크아웃
        rsi_curr = _val(current, self.rsi_col)
        rsi_prev = _val(prev, self.rsi_col)
        adx = _val(current, self.adx_col)
        macd = _val(current, self.macd_col)
        macds = _val(current, self.macds_col)
        vol = _val(current, 'volume')
        vol_ma = _val(current, self.vol_ma_col)
        if all(v is not None for v in (rsi_curr, rsi_prev, adx, macd, macds, vol, vol_ma)) and vol_ma > 0:
            rsi_cross_up = (rsi_prev <= self.rsi_threshold) and (rsi_curr > self.rsi_threshold)
            rsi_momentum = rsi_curr - rsi_prev > 5
            rsi_ok = rsi_cross_up or (rsi_curr > self.rsi_threshold and rsi_momentum)
            adx_ok = adx > self.adx_threshold
            macd_ok = macd > macds
            vol_ratio = vol / vol_ma
            vol_ok = vol_ratio > self.volume_multiplier
            is_met = rsi_ok and adx_ok and macd_ok and vol_ok
            triggers.append(("🔹 브레이크아웃", bool(is_met)))
            triggers.append((f"    RSI 돌파: {rsi_prev:.1f}→{rsi_curr:.1f} (기준>{self.rsi_threshold}↑ 또는 +5모멘텀)", bool(rsi_ok)))
            triggers.append((f"    ADX>{self.adx_threshold}: 현재 {adx:.1f}", bool(adx_ok)))
            triggers.append((f"    MACD>시그널: {macd:.1f}/{macds:.1f}", bool(macd_ok)))
            triggers.append((f"    거래량>{self.volume_multiplier}x: 현재 {vol_ratio:.1f}x", bool(vol_ok)))

        # 신호 2: 풀백 진입
        prev_ema20 = _val(prev, 'EMA_20')
        curr_ema20 = _val(current, 'EMA_20')
        prev_close = _val(prev, 'close')
        if all(v is not None for v in (adx, prev_ema20, prev_close, curr_ema20, macd, macds, vol, vol_ma)):
            adx_ok = adx > self.pullback_adx_threshold
            bounce_ok = prev_close < prev_ema20 and curr_price > curr_ema20
            macd_ok = macd > macds
            vol_ratio = vol / vol_ma if vol_ma > 0 else 0
            vol_ok = vol > vol_ma
            is_met = adx_ok and bounce_ok and macd_ok and vol_ok
            triggers.append(("🔹 풀백 진입", bool(is_met)))
            triggers.append((f"    ADX>{self.pullback_adx_threshold}: 현재 {adx:.1f}", bool(adx_ok)))
            triggers.append((f"    EMA20 반등: 이전종가{'<' if prev_close < prev_ema20 else '≥'}EMA20, 현재가{'>' if curr_price > curr_ema20 else '≤'}EMA20", bool(bounce_ok)))
            triggers.append((f"    MACD>시그널: {macd:.1f}/{macds:.1f}", bool(macd_ok)))
            triggers.append((f"    거래량>평균: {vol_ratio:.1f}x", bool(vol_ok)))

        return triggers

    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_sl_multiplier)
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * self.atr_tp_multiplier)
        return stop_loss, take_profit
