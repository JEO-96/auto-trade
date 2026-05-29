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
