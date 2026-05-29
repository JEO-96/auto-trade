"""Entry confirmation for the paper lab.

Reuses an existing, backtested strategy (read-only) to confirm whether a
candidate symbol is in a genuine surge before the paper lab buys it. This is
the gate that turns "buy the top 24h gainers" into "buy only confirmed setups".

The production strategy classes in ``core/strategies`` are NOT modified here;
we only call their ``apply_indicators`` / ``check_buy_signal``.
"""
from __future__ import annotations

from typing import Protocol

import pandas as pd

from core.strategy import get_strategy


class EntryConfirmer(Protocol):
    def confirm(self, symbol: str, df: pd.DataFrame) -> bool:
        ...


class StrategyConfirmer:
    """Confirm an entry using a backtested strategy's buy signal.

    ``min_rows`` guards strategies that require warmup history (SurgeCatcher
    needs current_idx >= 200). Symbols with insufficient candle history (e.g.
    freshly listed coins) are rejected — they cannot be confirmed or backtested.
    """

    def __init__(self, strategy_name: str = "surge_catcher_15m", min_rows: int = 201) -> None:
        self.strategy_name = strategy_name
        self.min_rows = min_rows
        self._strategy = get_strategy(strategy_name)

    def confirm(self, symbol: str, df: pd.DataFrame | None) -> bool:
        if df is None or len(df) < self.min_rows:
            return False
        prepared = self._strategy.apply_indicators(df.copy())
        return bool(self._strategy.check_buy_signal(prepared, len(prepared) - 1))


class EnsembleConfirmer:
    """Confirm an entry if ANY of several backtested strategies fires a buy.

    Used to pivot the paper lab onto the validated 4h trend-following edge:
    momentum_aggressive_4h + trend_rider_4h_v1 (both robust across universe
    subsets, out-of-sample, and walk-forward). Each strategy applies its own
    indicators on a fresh copy of the OHLCV frame.
    """

    def __init__(self, strategy_names: list[str], min_rows: int = 201) -> None:
        self.strategy_names = list(strategy_names)
        self.min_rows = min_rows
        self._strategies = [get_strategy(name) for name in self.strategy_names]

    def confirm(self, symbol: str, df: pd.DataFrame | None) -> bool:
        if df is None or len(df) < self.min_rows:
            return False
        for strat in self._strategies:
            prepared = strat.apply_indicators(df.copy())
            if strat.check_buy_signal(prepared, len(prepared) - 1):
                return True
        return False
