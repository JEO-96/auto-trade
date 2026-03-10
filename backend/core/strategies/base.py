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

        # Signal thresholds (overridden by subclasses)
        self.rsi_threshold: float = 60.0
        self.adx_threshold: float = 20.0
        self.volume_multiplier: float = 2.0

        # Exit parameters (overridden by subclasses)
        self.atr_sl_multiplier: float = 1.5
        self.atr_tp_multiplier: float = 3.0
        self.trailing_stop_multiplier: float = 1.5
        self.atr_fallback_pct: float = 0.02

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

    # ------------------------------------------------------------------
    # Common indicator application
    # ------------------------------------------------------------------
    def apply_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the shared set of technical indicators:
        RSI, MACD, Volume SMA, EMA (200/50/20), ATR(14), ADX(14).

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
        df['EMA_200'] = df.ta.ema(length=200)
        df['EMA_50'] = df.ta.ema(length=50)
        df['EMA_20'] = df.ta.ema(length=20)

        # Volatility
        atr_df = df.ta.atr(length=14)
        if atr_df is not None:
            df['ATR_14'] = atr_df

        # Trend strength
        adx_df = df.ta.adx(length=14)
        if adx_df is not None:
            df['ADX_14'] = adx_df['ADX_14']
            df['DMP_14'] = adx_df['DMP_14']
            df['DMN_14'] = adx_df['DMN_14']

        return df

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
        Retrieve ATR_14 at the given index.
        Falls back to a percentage of entry_price when ATR is missing/invalid.
        """
        if fallback_pct is None:
            fallback_pct = self.atr_fallback_pct
        atr = df.iloc[idx].get('ATR_14', None)
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
