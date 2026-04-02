"""
Ultimate Futures Strategy v3 — 주간 1.5%+ 목표

앙상블 스코링 시스템: 개별 시그널이 아닌 복합 점수 기반 진입
- EMA 트렌드 (추세 방향)
- RSI 과매수/과매도 + 다이버전스
- MACD 크로스 + 히스토그램 모멘텀
- 볼린저밴드 스퀴즈/브레이크아웃 + 평균회귀
- 피보나치 되돌림 수준 (동적 지지/저항)
- 캔들 패턴 (핀바, 장악형)
- ADX 추세 강도 + DI 방향
- Stochastic RSI 크로스
- 볼륨 프로파일
- 다중 시간대 확인 (EMA 200 장기 방향)

점수 임계값 시스템: 신호 품질에 따라 차등 진입
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
import logging

logger = logging.getLogger("okx_futures")


class SmartTrendFuturesStrategy:
    """앙상블 스코링 선물 전략"""

    def __init__(self):
        # === 지표 파라미터 ===
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2.0
        self.atr_period = 14
        self.adx_period = 14
        self.stoch_rsi_period = 14
        self.stoch_k = 3
        self.stoch_d = 3

        # EMA 길이
        self.ema_lengths = [9, 21, 55, 200]

        # 볼륨
        self.volume_ma_period = 20

        # === 스코링 임계값 (파라미터 스윕 최적화 결과) ===
        self.entry_threshold = 7        # 7점 이상만 진입 (고품질 신호만)
        self.strong_threshold = 8       # 8점 이상이면 강한 신호

        # === SL/TP (4년 BTC+ETH 최적화: SL=3.0 ATR, TP=4.0 ATR) ===
        # 일반 신호
        self.normal_sl_mult = 3.0       # ATR x 3.0
        self.normal_tp_mult = 4.0       # ATR x 4.0 (R:R = 1:1.33)
        # 강한 신호
        self.strong_sl_mult = 3.5       # ATR x 3.5
        self.strong_tp_mult = 5.5       # ATR x 5.5 (R:R = 1:1.57)

        self.max_sl_pct = 0.03          # 최대 SL 3%
        self.max_tp_pct = 0.08          # 최대 TP 8%

        # === 쿨다운 ===
        self.cooldown_bars = 3
        self._last_exit_idx = -100

        # === 리스크 (4년 최적화: thr=7, risk=0.05) ===
        self.leverage = 3
        self.risk_per_trade = 0.05      # 거래당 5% 리스크
        self.risk_strong_trade = 0.06   # 강한 신호는 6%

        # === 피보나치 수준 ===
        self.fib_lookback = 50          # 피보나치 고저 탐색 범위
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]

    # ================================================================
    # 지표 적용
    # ================================================================
    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """모든 기술적 지표 적용"""
        # EMAs
        for length in self.ema_lengths:
            ema = df.ta.ema(length=length)
            df[f"EMA_{length}"] = ema if ema is not None else np.nan

        # RSI
        df["RSI"] = df.ta.rsi(length=self.rsi_period)

        # Stochastic RSI
        stoch_rsi = df.ta.stochrsi(
            length=self.stoch_rsi_period, rsi_length=self.rsi_period,
            k=self.stoch_k, d=self.stoch_d
        )
        if stoch_rsi is not None:
            df["STOCH_K"] = stoch_rsi.iloc[:, 0]
            df["STOCH_D"] = stoch_rsi.iloc[:, 1]

        # MACD
        macd_df = df.ta.macd(
            fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal
        )
        if macd_df is not None:
            df["MACD"] = macd_df.iloc[:, 0]
            df["MACD_signal"] = macd_df.iloc[:, 1]
            df["MACD_hist"] = macd_df.iloc[:, 2]

        # Bollinger Bands
        bb_df = df.ta.bbands(length=self.bb_period, std=self.bb_std)
        if bb_df is not None:
            df["BB_upper"] = bb_df.iloc[:, 0]
            df["BB_mid"] = bb_df.iloc[:, 1]
            df["BB_lower"] = bb_df.iloc[:, 2]
            df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_mid"]
            # %B (가격의 밴드 내 위치)
            bb_range = df["BB_upper"] - df["BB_lower"]
            df["BB_pctB"] = np.where(bb_range > 0, (df["close"] - df["BB_lower"]) / bb_range, 0.5)

        # ATR
        df["ATR"] = df.ta.atr(length=self.atr_period)

        # ADX + DI
        adx_df = df.ta.adx(length=self.adx_period)
        if adx_df is not None:
            df["ADX"] = adx_df.iloc[:, 0]
            df["DMP"] = adx_df.iloc[:, 1]
            df["DMN"] = adx_df.iloc[:, 2]

        # Volume MA
        df["VOL_MA"] = df.ta.sma(close=df["volume"], length=self.volume_ma_period)

        # 피보나치 레벨 (동적)
        df = self._calc_fibonacci_levels(df)

        # RSI 다이버전스 (간소화)
        df = self._calc_rsi_divergence(df)

        return df

    def _calc_fibonacci_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """롤링 윈도우 기반 동적 피보나치 되돌림 수준"""
        lb = self.fib_lookback
        highs = df["high"].rolling(lb).max()
        lows = df["low"].rolling(lb).min()
        diff = highs - lows

        for level in self.fib_levels:
            # 상승 되돌림 (고점에서 하락)
            df[f"FIB_{level}_support"] = highs - diff * level
            # 하락 되돌림 (저점에서 상승)
            df[f"FIB_{level}_resist"] = lows + diff * level

        return df

    def _calc_rsi_divergence(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI 다이버전스 감지 (간소화)"""
        df["RSI_bull_div"] = False
        df["RSI_bear_div"] = False

        rsi = df["RSI"]
        close = df["close"]

        for i in range(20, len(df)):
            if pd.isna(rsi.iloc[i]) or pd.isna(rsi.iloc[i - 10]):
                continue
            # 불리시 다이버전스: 가격 저점 갱신, RSI 저점 미갱신
            price_lower = close.iloc[i] < close.iloc[i - 10:i].min()
            rsi_higher = rsi.iloc[i] > rsi.iloc[i - 10:i].min()
            if price_lower and rsi_higher and rsi.iloc[i] < 40:
                df.iloc[i, df.columns.get_loc("RSI_bull_div")] = True

            # 베어리시 다이버전스: 가격 고점 갱신, RSI 고점 미갱신
            price_higher = close.iloc[i] > close.iloc[i - 10:i].max()
            rsi_lower = rsi.iloc[i] < rsi.iloc[i - 10:i].max()
            if price_higher and rsi_lower and rsi.iloc[i] > 60:
                df.iloc[i, df.columns.get_loc("RSI_bear_div")] = True

        return df

    # ================================================================
    # 앙상블 스코링
    # ================================================================
    def check_signal(self, df: pd.DataFrame, idx: int) -> str | None:
        """앙상블 스코어 기반 진입 판단 (동적 임계값 + 다중 필터)"""
        if idx < 200:
            return None

        if idx - self._last_exit_idx < self.cooldown_bars:
            return None

        curr = df.iloc[idx]
        close = curr.get("close", 0)
        if close <= 0:
            return None

        # ── 동적 임계값: 변동성 높으면 더 높은 점수 요구 ──
        atr = curr.get("ATR", None)
        threshold = self.entry_threshold  # 기본 7
        if atr is not None and not pd.isna(atr) and close > 0:
            atr_pct = atr / close
            if atr_pct > 0.012:        # ATR > 1.2% → 고변동
                threshold = 8
            elif atr_pct > 0.011:      # ATR > 1.1% → 중변동
                threshold = self.entry_threshold + 1  # 8

        # ── 추세-신호 정합성: EMA200 반대 방향이면 +1 추가 요구 ──
        ema200 = curr.get("EMA_200", np.nan)
        counter_trend_penalty = 0
        if not pd.isna(ema200):
            # 롱인데 EMA200 아래, 숏인데 EMA200 위 → 역추세
            counter_trend_penalty = 1  # 아래에서 적용

        long_score = self._calc_long_score(df, idx)
        short_score = self._calc_short_score(df, idx)

        # 역추세 페널티 적용
        long_threshold = threshold + (counter_trend_penalty if not pd.isna(ema200) and close < ema200 else 0)
        short_threshold = threshold + (counter_trend_penalty if not pd.isna(ema200) and close > ema200 else 0)

        signal = None
        if long_score >= long_threshold and long_score > short_score:
            signal = "long"
        elif short_score >= short_threshold and short_score > long_score:
            signal = "short"

        if signal is None:
            return None

        # ── 캔들 방향 확인: 시그널 봉이 진입 방향으로 마감 ──
        candle_bullish = curr["close"] > curr["open"]
        candle_bearish = curr["close"] < curr["open"]
        if signal == "long" and not candle_bullish:
            return None
        if signal == "short" and not candle_bearish:
            return None

        # ── 다중 봉 확인: 최근 3봉 중 2봉 이상이 방향 지지 ──
        support_count = 0
        for k in range(max(0, idx - 2), idx + 1):
            row = df.iloc[k]
            if signal == "long" and row["close"] > row["open"]:
                support_count += 1
            elif signal == "short" and row["close"] < row["open"]:
                support_count += 1
        if support_count < 2:
            return None

        score = long_score if signal == "long" else short_score
        strength = "강" if score >= self.strong_threshold else "일반"
        logger.info(
            f"{signal.upper()} [{strength}] score={score}/10 thr={long_threshold if signal=='long' else short_threshold} | "
            f"close={close:.4f}"
        )
        return signal

    def _calc_long_score(self, df: pd.DataFrame, idx: int) -> int:
        """롱 진입 점수 계산 (0~10)"""
        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        score = 0

        close = curr.get("close", 0)
        if close == 0:
            return 0

        # 1. EMA 추세 정렬 (+1)
        ema9 = curr.get("EMA_9", np.nan)
        ema21 = curr.get("EMA_21", np.nan)
        ema55 = curr.get("EMA_55", np.nan)
        if not any(pd.isna(v) for v in [ema9, ema21, ema55]):
            if ema9 > ema21 > ema55:
                score += 1

        # 2. 가격 > EMA200 (장기 상승) (+1)
        ema200 = curr.get("EMA_200", np.nan)
        if not pd.isna(ema200) and close > ema200:
            score += 1

        # 3. RSI 적정 구간 (30~60 = 반등 여력) (+1)
        rsi = curr.get("RSI", np.nan)
        if not pd.isna(rsi):
            if 30 < rsi < 60:
                score += 1

        # 4. RSI 불리시 다이버전스 (+1)
        if curr.get("RSI_bull_div", False):
            score += 1

        # 5. MACD 양전환 또는 양수 가속 (+1)
        macd_hist = curr.get("MACD_hist", np.nan)
        prev_macd = prev.get("MACD_hist", np.nan)
        if not any(pd.isna(v) for v in [macd_hist, prev_macd]):
            if (prev_macd <= 0 < macd_hist) or (macd_hist > 0 and macd_hist > prev_macd):
                score += 1

        # 6. Stochastic RSI 상향 크로스 (+1)
        stoch_k = curr.get("STOCH_K", np.nan)
        stoch_d = curr.get("STOCH_D", np.nan)
        prev_k = prev.get("STOCH_K", np.nan)
        prev_d = prev.get("STOCH_D", np.nan)
        if not any(pd.isna(v) for v in [stoch_k, stoch_d, prev_k, prev_d]):
            if prev_k <= prev_d and stoch_k > stoch_d and stoch_k < 80:
                score += 1

        # 7. 볼린저밴드 하단 근접 또는 %B < 0.2 (+1)
        bb_pctB = curr.get("BB_pctB", np.nan)
        if not pd.isna(bb_pctB) and bb_pctB < 0.25:
            score += 1

        # 8. ADX 상승 + DI+ > DI- (+1)
        adx = curr.get("ADX", np.nan)
        dmp = curr.get("DMP", np.nan)
        dmn = curr.get("DMN", np.nan)
        if not any(pd.isna(v) for v in [adx, dmp, dmn]):
            if dmp > dmn and adx > 18:
                score += 1

        # 9. 피보나치 지지 근접 (+1)
        for level in [0.618, 0.5, 0.382]:
            fib_sup = curr.get(f"FIB_{level}_support", np.nan)
            if not pd.isna(fib_sup):
                proximity = abs(close - fib_sup) / close
                if proximity < 0.008:  # 0.8% 이내
                    score += 1
                    break

        # 10. 볼륨 확인 (평균 이상) (+1)
        vol = curr.get("volume", 0)
        vol_ma = curr.get("VOL_MA", np.nan)
        if not pd.isna(vol_ma) and vol_ma > 0 and vol > vol_ma * 0.8:
            score += 1

        return score

    def _calc_short_score(self, df: pd.DataFrame, idx: int) -> int:
        """숏 진입 점수 계산 (0~10)"""
        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        score = 0

        close = curr.get("close", 0)
        if close == 0:
            return 0

        # 1. EMA 역배열 (+1)
        ema9 = curr.get("EMA_9", np.nan)
        ema21 = curr.get("EMA_21", np.nan)
        ema55 = curr.get("EMA_55", np.nan)
        if not any(pd.isna(v) for v in [ema9, ema21, ema55]):
            if ema9 < ema21 < ema55:
                score += 1

        # 2. 가격 < EMA200 (장기 하락) (+1)
        ema200 = curr.get("EMA_200", np.nan)
        if not pd.isna(ema200) and close < ema200:
            score += 1

        # 3. RSI 적정 구간 (40~70 = 하락 여력) (+1)
        rsi = curr.get("RSI", np.nan)
        if not pd.isna(rsi):
            if 40 < rsi < 70:
                score += 1

        # 4. RSI 베어리시 다이버전스 (+1)
        if curr.get("RSI_bear_div", False):
            score += 1

        # 5. MACD 음전환 또는 음수 가속 (+1)
        macd_hist = curr.get("MACD_hist", np.nan)
        prev_macd = prev.get("MACD_hist", np.nan)
        if not any(pd.isna(v) for v in [macd_hist, prev_macd]):
            if (prev_macd >= 0 > macd_hist) or (macd_hist < 0 and macd_hist < prev_macd):
                score += 1

        # 6. Stochastic RSI 하향 크로스 (+1)
        stoch_k = curr.get("STOCH_K", np.nan)
        stoch_d = curr.get("STOCH_D", np.nan)
        prev_k = prev.get("STOCH_K", np.nan)
        prev_d = prev.get("STOCH_D", np.nan)
        if not any(pd.isna(v) for v in [stoch_k, stoch_d, prev_k, prev_d]):
            if prev_k >= prev_d and stoch_k < stoch_d and stoch_k > 20:
                score += 1

        # 7. 볼린저밴드 상단 근접 또는 %B > 0.8 (+1)
        bb_pctB = curr.get("BB_pctB", np.nan)
        if not pd.isna(bb_pctB) and bb_pctB > 0.75:
            score += 1

        # 8. ADX 상승 + DI- > DI+ (+1)
        adx = curr.get("ADX", np.nan)
        dmp = curr.get("DMP", np.nan)
        dmn = curr.get("DMN", np.nan)
        if not any(pd.isna(v) for v in [adx, dmp, dmn]):
            if dmn > dmp and adx > 18:
                score += 1

        # 9. 피보나치 저항 근접 (+1)
        for level in [0.618, 0.5, 0.382]:
            fib_res = curr.get(f"FIB_{level}_resist", np.nan)
            if not pd.isna(fib_res):
                proximity = abs(close - fib_res) / close
                if proximity < 0.008:
                    score += 1
                    break

        # 10. 볼륨 확인 (+1)
        vol = curr.get("volume", 0)
        vol_ma = curr.get("VOL_MA", np.nan)
        if not pd.isna(vol_ma) and vol_ma > 0 and vol > vol_ma * 0.8:
            score += 1

        return score

    def get_signal_score(self, df: pd.DataFrame, idx: int) -> tuple[int, int]:
        """현재 롱/숏 스코어 반환"""
        return self._calc_long_score(df, idx), self._calc_short_score(df, idx)

    # ================================================================
    # Exit / Position Sizing
    # ================================================================
    def set_last_exit(self, idx: int):
        self._last_exit_idx = idx

    def calculate_exit_levels(
        self, df: pd.DataFrame, idx: int, entry_price: float, side: str
    ) -> tuple[float, float]:
        """스코어 기반 SL/TP (강한 신호 = 넓은 TP)"""
        atr = df.iloc[idx].get("ATR", None)
        if atr is None or pd.isna(atr) or atr <= 0:
            atr = entry_price * 0.012

        long_score, short_score = self.get_signal_score(df, idx)
        score = long_score if side == "long" else short_score
        is_strong = score >= self.strong_threshold

        if is_strong:
            sl_dist = min(atr * self.strong_sl_mult, entry_price * self.max_sl_pct)
            tp_dist = min(atr * self.strong_tp_mult, entry_price * self.max_tp_pct)
        else:
            sl_dist = min(atr * self.normal_sl_mult, entry_price * self.max_sl_pct)
            tp_dist = min(atr * self.normal_tp_mult, entry_price * self.max_tp_pct)

        tp_dist = max(tp_dist, entry_price * 0.015)

        if side == "long":
            return entry_price - sl_dist, entry_price + tp_dist
        else:
            return entry_price + sl_dist, entry_price - tp_dist

    def calculate_position_size(
        self, account_balance: float, entry_price: float, stop_loss: float
    ) -> float:
        risk_amount = account_balance * self.risk_per_trade
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return 0.0
        position_size = risk_amount / sl_distance
        return max(round(position_size, 3), 0.001)

    def get_signal_summary(self, df: pd.DataFrame, idx: int) -> dict:
        curr = df.iloc[idx]
        long_s, short_s = self.get_signal_score(df, idx)
        ema21 = curr.get("EMA_21", 0)
        ema55 = curr.get("EMA_55", 0)
        return {
            "close": curr.get("close"),
            "long_score": long_s,
            "short_score": short_s,
            "rsi": curr.get("RSI"),
            "macd_hist": curr.get("MACD_hist"),
            "adx": curr.get("ADX"),
            "atr": curr.get("ATR"),
            "bb_pctB": curr.get("BB_pctB"),
            "stoch_k": curr.get("STOCH_K"),
            "vol_ratio": (
                curr["volume"] / curr["VOL_MA"]
                if curr.get("VOL_MA") and curr["VOL_MA"] > 0
                else None
            ),
            "trend": "UP" if ema21 > ema55 else "DOWN",
        }
