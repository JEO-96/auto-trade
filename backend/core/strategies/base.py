"""
BaseStrategy - Abstract base class for all momentum breakout strategies.

Centralizes common indicator application, NaN validation, ATR fallback,
and trailing stop logic. Subclasses override signal and exit methods.
"""
from abc import ABC, abstractmethod
import pandas as pd
import pandas_ta as ta
import numpy as np
from core import config


class BaseStrategy(ABC):
    """
    Abstract base for momentum breakout strategies.

    Subclasses must implement:
        - check_buy_signal(df, current_idx) -> bool
        - calculate_exit_levels(df, entry_idx, entry_price) -> (stop_loss, take_profit)
    """

    def __init__(self):
        self.use_trailing_stop: bool = False

        # Indicator parameters (default to config values)
        self.rsi_period: int = config.RSI_PERIOD
        self.macd_fast: int = config.MACD_FAST
        self.macd_slow: int = config.MACD_SLOW
        self.macd_signal: int = config.MACD_SIGNAL
        self.volume_ma_period: int = config.VOLUME_MA_PERIOD
        self.atr_period: int = 14
        self.adx_period: int = 14

        # Signal thresholds (overridden by subclasses)
        self.rsi_threshold: float = 60.0
        self.adx_threshold: float = 20.0
        self.volume_multiplier: float = 2.0

        # Exit parameters (overridden by subclasses)
        self.atr_sl_multiplier: float = 1.5
        self.atr_tp_multiplier: float = 3.0
        self.trailing_stop_multiplier: float = 1.5
        self.atr_fallback_pct: float = 0.02

        # Backtest SL/TP percentages for vectorbt (per-strategy override)
        # None = no SL/TP applied in backtest for that side
        self.backtest_sl_pct: float | None = 0.015   # 1.5% default
        self.backtest_tp_pct: float | None = 0.03    # 3.0% default

        # ── Filter condition flags (텔레그램 체크리스트용) ──
        # 서브클래스 __init__에서 실제 진입 필터에 맞게 설정
        self.filter_close_gt_ema200: bool = False
        self.filter_ema50_gt_ema200: bool = False
        self.filter_ema20_gt_ema50: bool = False
        self.filter_close_gt_ema20: bool = False
        self.filter_close_gt_ema100: bool = False
        self.filter_triple_ema: bool = False      # EMA20 > EMA50 > EMA200
        self.filter_di_positive: bool = False
        self.filter_macd_gt_signal: bool = False
        self.filter_rsi_max: float | None = None   # RSI < value
        self.filter_adx_min: float | None = None   # ADX > value
        self.filter_volume_min: float | None = None  # volume > avg * value

    # ------------------------------------------------------------------
    # Column name helpers
    # ------------------------------------------------------------------
    @property
    def rsi_col(self) -> str:
        return f"RSI_{self.rsi_period}"

    @property
    def macd_col(self) -> str:
        return f"MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"

    @property
    def macds_col(self) -> str:
        return f"MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}"

    @property
    def vol_ma_col(self) -> str:
        return f"VOL_SMA_{self.volume_ma_period}"

    @property
    def atr_col(self) -> str:
        return f"ATR_{self.atr_period}"

    @property
    def adx_col(self) -> str:
        return f"ADX_{self.adx_period}"

    @property
    def dmp_col(self) -> str:
        return f"DMP_{self.adx_period}"

    @property
    def dmn_col(self) -> str:
        return f"DMN_{self.adx_period}"

    # ------------------------------------------------------------------
    # Common indicator application
    # ------------------------------------------------------------------
    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the shared set of technical indicators:
        RSI, MACD, Volume SMA, EMA (200/50/20), ATR, ADX.

        Subclasses can call super().apply_indicators(df) and then add
        additional indicators.
        """
        df.ta.rsi(length=self.rsi_period, append=True)
        df.ta.macd(
            fast=self.macd_fast,
            slow=self.macd_slow,
            signal=self.macd_signal,
            append=True,
        )
        df[self.vol_ma_col] = df.ta.sma(
            close=df['volume'], length=self.volume_ma_period
        )

        # Trend EMAs
        for length, col in [(200, 'EMA_200'), (50, 'EMA_50'), (20, 'EMA_20')]:
            ema = df.ta.ema(length=length)
            if ema is None:
                df[col] = np.nan
            elif hasattr(ema, 'iloc') and ema.ndim > 1:
                df[col] = ema.iloc[:, 0]
            else:
                df[col] = ema

        # Volatility
        atr_df = df.ta.atr(length=self.atr_period)
        if atr_df is not None:
            df[self.atr_col] = atr_df

        # Trend strength
        adx_df = df.ta.adx(length=self.adx_period)
        if adx_df is not None:
            adx_suffix = f"_{self.adx_period}"
            df[self.adx_col] = adx_df[f'ADX{adx_suffix}']
            df[self.dmp_col] = adx_df[f'DMP{adx_suffix}']
            df[self.dmn_col] = adx_df[f'DMN{adx_suffix}']

        return df

    # ------------------------------------------------------------------
    # Telegram condition checklist
    # ------------------------------------------------------------------
    def get_entry_conditions(
        self, df: pd.DataFrame, current_idx: int, curr_price: float
    ) -> list[tuple[str, bool]]:
        """Return list of (label, is_met) tuples for Telegram feedback.

        Built automatically from ``filter_*`` flags set in subclass __init__.
        Override in subclass for fully custom conditions.
        """
        current = df.iloc[current_idx]
        conditions: list[tuple[str, bool]] = []

        def _val(col: str):
            v = current.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            return v

        if self.filter_close_gt_ema200:
            ema200 = _val('EMA_200')
            if ema200 is not None:
                conditions.append(("가격>EMA200", curr_price > ema200))

        if self.filter_ema50_gt_ema200:
            ema50, ema200 = _val('EMA_50'), _val('EMA_200')
            if ema50 is not None and ema200 is not None:
                conditions.append(("골든크로스(EMA50>200)", ema50 > ema200))

        if self.filter_triple_ema:
            ema20, ema50, ema200 = _val('EMA_20'), _val('EMA_50'), _val('EMA_200')
            if all(v is not None for v in (ema20, ema50, ema200)):
                conditions.append(("EMA정배열(20>50>200)", ema20 > ema50 > ema200))
        elif self.filter_ema20_gt_ema50:
            ema20, ema50 = _val('EMA_20'), _val('EMA_50')
            if ema20 is not None and ema50 is not None:
                conditions.append(("EMA정배열(20>50)", ema20 > ema50))

        if self.filter_close_gt_ema100:
            ema100 = _val('EMA_100')
            if ema100 is not None:
                conditions.append(("가격>EMA100", curr_price > ema100))

        if self.filter_close_gt_ema20:
            ema20 = _val('EMA_20')
            if ema20 is not None:
                conditions.append(("가격>EMA20", curr_price > ema20))

        if self.filter_di_positive:
            dmp, dmn = _val(self.dmp_col), _val(self.dmn_col)
            if dmp is not None and dmn is not None:
                conditions.append((f"DI+>DI- ({dmp:.1f}/{dmn:.1f})", dmp > dmn))

        if self.filter_rsi_max is not None:
            rsi = _val(self.rsi_col)
            if rsi is not None:
                conditions.append((f"RSI<{self.filter_rsi_max} (현재 {rsi:.1f})", rsi < self.filter_rsi_max))

        if self.filter_adx_min is not None:
            adx = _val(self.adx_col)
            if adx is not None:
                conditions.append((f"ADX>{self.filter_adx_min} (현재 {adx:.1f})", adx > self.filter_adx_min))

        if self.filter_macd_gt_signal:
            macd, macds = _val(self.macd_col), _val(self.macds_col)
            if macd is not None and macds is not None:
                conditions.append(("MACD>시그널", macd > macds))

        if self.filter_volume_min is not None:
            vol, vol_ma = _val('volume'), _val(self.vol_ma_col)
            if vol is not None and vol_ma is not None and vol_ma > 0:
                ratio = vol / vol_ma
                conditions.append((f"거래량>{self.filter_volume_min}x (현재 {ratio:.1f}x)", vol >= vol_ma * self.filter_volume_min))

        return conditions

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------
    @abstractmethod
    def check_buy_signal(self, df: pd.DataFrame, current_idx: int) -> bool:
        """Return True when buy conditions are met at current_idx."""
        ...

    @abstractmethod
    def calculate_exit_levels(
        self, df: pd.DataFrame, entry_idx: int, entry_price: float
    ) -> tuple:
        """Return (stop_loss, take_profit) for a position entered at entry_price."""
        ...

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------
    def _get_atr_or_fallback(
        self, df: pd.DataFrame, idx: int, entry_price: float, fallback_pct: float = None
    ) -> float:
        """
        Retrieve ATR at the given index.
        Falls back to a percentage of entry_price when ATR is missing/invalid.
        """
        if fallback_pct is None:
            fallback_pct = self.atr_fallback_pct
        atr = df.iloc[idx].get(self.atr_col, None)
        if atr is None or pd.isna(atr) or atr <= 0:
            atr = entry_price * fallback_pct
        return atr

    def _validate_indicators(self, row: pd.Series, required_cols: list) -> bool:
        """
        Return True if all required_cols exist in row and are not NaN.
        """
        for col in required_cols:
            val = row.get(col)
            if val is None or pd.isna(val):
                return False
        return True

    def update_trailing_stop(
        self, current_price: float, current_atr: float, current_sl: float
    ) -> float:
        """
        Default trailing-stop update using ATR and trailing_stop_multiplier.
        Returns the higher of current_sl and the new computed stop.
        """
        if current_atr <= 0 or pd.isna(current_atr):
            return current_sl
        new_sl = current_price - (current_atr * self.trailing_stop_multiplier)
        return max(current_sl, new_sl)

    def get_risk_multiplier(self, df: pd.DataFrame, current_idx: int) -> float:
        """
        Default risk multiplier. Subclasses override to scale position size
        based on market conditions.
        """
        return 1.0
