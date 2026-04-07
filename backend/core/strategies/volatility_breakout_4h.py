import pandas as pd
import numpy as np
from core import config
from core.strategies.base import BaseStrategy


class VolatilityBreakout4hStrategy(BaseStrategy):
    """
    Volatility Breakout 4h - 변동성 수축 후 돌파 전략 (알트코인 범용)

    핵심 아이디어:
    코인 가격은 "수축 → 확장" 사이클을 반복한다.
    볼린저 밴드가 좁아질 때(수축) 기다렸다가,
    상단 돌파 + 거래량 급증 시 진입 = 새 추세의 시작점 포착.

    V1과의 근본적 차이:
    - V1: 이미 추세 중인 시장에서 눌림목 진입 (추세 추종)
    - 이 전략: 횡보 후 방향이 정해지는 순간 진입 (돌파)

    진입 조건 (AND):
    1. 볼린저 밴드 수축: BB width가 최근 20봉 중 하위 30% (에너지 축적)
    2. 상단 돌파: 종가 > BB 상단 (방향 결정)
    3. 거래량 확인: 현재 거래량 > 20봉 평균 * 1.5 (진짜 돌파)
    4. RSI 확인: 40 < RSI < 75 (모멘텀 있되 과열 아님)
    5. MACD 양수: MACD > 0 (상승 모멘텀 배경)

    청산:
    - ATR 기반 적응형 트레일링 스탑 (코인별 변동성 자동 대응)
    - 고정 손절: 진입가 대비 ATR * 2 하락 시
    """

    def __init__(self):
        super().__init__()
        self.use_trailing_stop = True

        # 볼린저 밴드 파라미터
        self.bb_period = 20
        self.bb_std = 2.0
        self.squeeze_percentile = 30  # BB width 하위 30%면 수축

        # 거래량 돌파 배수
        self.volume_breakout_ratio = 1.5

        # RSI 범위
        self.rsi_lower = 40
        self.rsi_upper = 75

        # ATR 기반 트레일링 (코인별 자동 적응)
        self.atr_trail_multiplier = 2.5
        self.min_trail_pct = 0.04   # 최소 4%
        self.max_trail_pct = 0.15   # 최대 15%

        # 백테스트 파라미터
        self.backtest_sl_pct = 0.07    # 폴백 SL 7%
        self.backtest_tp_pct = None    # TP 없음 (트레일링)
        self.backtest_trailing = True

        # 텔레그램 체크리스트
        self.filter_rsi_max = 75
        self.filter_volume_min = 1.5

    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기본 지표 + 볼린저 밴드 추가"""
        df = super().apply_indicators(df)

        # 볼린저 밴드
        bb = df.ta.bbands(length=self.bb_period, std=self.bb_std)
        if bb is not None and not bb.empty:
            bb_cols = bb.columns.tolist()
            # BBL, BBM, BBU, BBB, BBP 순서
            df['BB_lower'] = bb.iloc[:, 0]
            df['BB_mid'] = bb.iloc[:, 1]
            df['BB_upper'] = bb.iloc[:, 2]
            df['BB_width'] = bb.iloc[:, 3] if len(bb_cols) > 3 else (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1]
        else:
            df['BB_lower'] = np.nan
            df['BB_mid'] = np.nan
            df['BB_upper'] = np.nan
            df['BB_width'] = np.nan

        return df

    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < 50:
            return False

        current = df.iloc[current_idx]

        # 필수 지표 검증
        required = [self.rsi_col, self.macd_col, self.vol_ma_col,
                    'BB_upper', 'BB_width', self.atr_col]
        if not self._validate_indicators(current, required):
            return False
        if current.get(self.vol_ma_col, 0) == 0:
            return False

        price = current['close']
        bb_upper = current['BB_upper']
        bb_width = current['BB_width']
        rsi = current[self.rsi_col]
        macd = current[self.macd_col]
        volume = current['volume']
        vol_ma = current[self.vol_ma_col]

        # ========== 조건 1: 볼린저 밴드 수축 (에너지 축적) ==========
        # 최근 20봉의 BB width 중 현재가 하위 30%인지 확인
        lookback = min(20, current_idx)
        recent_widths = [df.iloc[current_idx - i].get('BB_width', np.nan) for i in range(lookback)]
        recent_widths = [w for w in recent_widths if w is not None and not pd.isna(w)]

        if len(recent_widths) < 5:
            return False

        width_threshold = np.percentile(recent_widths, self.squeeze_percentile)
        # 이전 봉에서 수축 상태였어야 함 (현재 봉에서 돌파)
        prev_width = df.iloc[current_idx - 1].get('BB_width')
        if prev_width is None or pd.isna(prev_width):
            return False
        if prev_width > width_threshold:
            return False  # 이전 봉이 수축 상태가 아니면 돌파가 아님

        # ========== 조건 2: BB 상단 돌파 ==========
        if price <= bb_upper:
            return False

        # ========== 조건 3: 거래량 급증 ==========
        if volume < vol_ma * self.volume_breakout_ratio:
            return False

        # ========== 조건 4: RSI 밴드 (모멘텀 확인) ==========
        if rsi < self.rsi_lower or rsi > self.rsi_upper:
            return False

        # ========== 조건 5: MACD 양수 (상승 배경) ==========
        if macd <= 0:
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

        # BB 수축
        bb_width = _val(current, 'BB_width')
        prev_width = _val(prev, 'BB_width')
        if bb_width is not None:
            triggers.append((f"📐 BB 폭: {bb_width:.4f} (이전: {prev_width:.4f})", True))

        # BB 상단 돌파
        bb_upper = _val(current, 'BB_upper')
        if bb_upper is not None:
            broke_out = curr_price > bb_upper
            triggers.append((f"🔹 BB 상단 돌파: {curr_price:,.0f} {'>' if broke_out else '≤'} {bb_upper:,.0f}", bool(broke_out)))

        # 거래량
        vol = _val(current, 'volume')
        vol_ma = _val(current, self.vol_ma_col)
        if vol is not None and vol_ma is not None and vol_ma > 0:
            ratio = vol / vol_ma
            is_met = ratio >= self.volume_breakout_ratio
            triggers.append((f"🔹 거래량 돌파: {ratio:.1f}x (기준: {self.volume_breakout_ratio}x)", bool(is_met)))

        # RSI
        rsi = _val(current, self.rsi_col)
        if rsi is not None:
            in_range = self.rsi_lower < rsi < self.rsi_upper
            triggers.append((f"🔹 RSI 범위: {rsi:.1f} ({'OK' if in_range else 'OUT'})", bool(in_range)))

        # MACD
        macd = _val(current, self.macd_col)
        if macd is not None:
            is_pos = macd > 0
            triggers.append((f"🔹 MACD 양수: {macd:,.0f} ({'>' if is_pos else '≤'} 0)", bool(is_pos)))

        # ATR 트레일링 표시
        atr_val = _val(current, self.atr_col)
        if atr_val is not None and curr_price > 0:
            trail_pct = min(self.max_trail_pct, max(self.min_trail_pct,
                           (atr_val / curr_price) * self.atr_trail_multiplier)) * 100
            triggers.append((f"📐 ATR 트레일링: {trail_pct:.1f}%", True))

        return triggers

    def calculate_exit_levels(self, df: pd.DataFrame, entry_idx: int, entry_price: float):
        atr = self._get_atr_or_fallback(df, entry_idx, entry_price)
        stop_loss = entry_price - (atr * self.atr_trail_multiplier)
        take_profit = entry_price + (atr * 4.0)  # R:R = 1:1.6 이상
        return stop_loss, take_profit
