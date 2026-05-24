import numpy as np
import pandas as pd
import vectorbt as vbt
import gc
from typing import List, Dict, Any, Type
import logging
from core.strategies.base import BaseStrategy
from core.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

class OptimizationEngine:
    """
    Engine for running grid search optimizations using vectorbt's broadcasting capabilities.
    Designed to be memory-efficient for low-RAM environments.
    """

    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size

    async def run_grid_search(
        self,
        strategy_class: Type[BaseStrategy],
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        param_grid: Dict[str, List[Any]],
        metric: str = "sharpe_ratio",
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Runs a grid search across the provided parameter grid.
        """
        # 1. Fetch data
        fetcher = DataFetcher()
        df = await fetcher.fetch_ohlcv(symbol, interval, start_date, end_date)
        if df.empty:
            raise ValueError(f"No data found for {symbol} {interval}")

        # Ensure float32 for memory efficiency
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(np.float32)

        # 2. Generate parameter combinations
        import itertools
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        total_combos = len(combinations)
        
        logger.info(f"Starting Grid Search: {total_combos} combinations for {symbol}")

        all_results = []

        # 3. Process in chunks
        for i in range(0, total_combos, self.chunk_size):
            chunk = combinations[i : i + self.chunk_size]
            chunk_results = self._run_chunk(strategy_class, df, keys, chunk)
            all_results.extend(chunk_results)
            
            # Explicit GC
            gc.collect()
            logger.info(f"Processed chunk {i//self.chunk_size + 1}, Total results so far: {len(all_results)}")

        # 4. Sort and return top N
        # We want to maximize the metric
        reverse_sort = True
        if metric in ['max_drawdown']: # Add other metrics that should be minimized
             reverse_sort = False

        sorted_results = sorted(all_results, key=lambda x: x.get(metric, -np.inf), reverse=reverse_sort)
        
        return sorted_results[:top_n]

    def _run_chunk(
        self, 
        strategy_class: Type[BaseStrategy], 
        df: pd.DataFrame, 
        param_names: List[str], 
        combinations: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Runs a single chunk of parameter combinations.
        """
        results = []
        
        # We could use vectorbt's native Param logic here for even better performance,
        # but to keep it compatible with existing BaseStrategy signal logic without 
        # rewriting every strategy, we optimize at the portfolio level.
        
        # Pre-calculate indicators on the base data once if possible, 
        # but many indicators depend on params.
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            # Instantiate strategy with params
            strat = strategy_class()
            for k, v in params.items():
                setattr(strat, k, v)
            
            # Apply indicators
            # Strategy apply_indicators usually modifies DF in-place or returns a copy
            # Here we copy to avoid cross-talk between combinations
            strat_df = df.copy()
            strat_df = strat.apply_indicators(strat_df)
            
            # Generate signals (Vectorized)
            # Most strategies currently have check_buy_signal(df, idx)
            # We need a vectorized version or a loop. 
            # For grid search efficiency, we'll try to find any existing vectorized signal method
            # or use a simple loop if not found (though less efficient).
            
            entries = self._generate_signals_vectorized(strat, strat_df)
            
            if entries.sum() == 0:
                # No trades, skips backtest to save time
                res = {**params}
                res.update({
                    "total_return": 0.0,
                    "sharpe_ratio": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "trade_count": 0
                })
                results.append(res)
                continue

            # Run Backtest with vectorbt
            pf = vbt.Portfolio.from_signals(
                strat_df['close'],
                entries=entries,
                exits=None, # Use SL/TP logic
                sl_stop=strat.backtest_sl_pct if hasattr(strat, 'backtest_sl_pct') else None,
                tp_stop=strat.backtest_tp_pct if hasattr(strat, 'backtest_tp_pct') else None,
                freq='1H', # Should match interval ideally
                fees=0.0006, # 0.06% taker fee
                init_cash=10000
            )
            
            stats = pf.stats()
            
            res = {**params}
            res.update({
                "total_return": float(pf.total_return()),
                "sharpe_ratio": float(stats.get('Sharpe Ratio', 0)),
                "win_rate": float(stats.get('Win Rate [%]', 0)),
                "max_drawdown": float(stats.get('Max Drawdown [%]', 0)),
                "trade_count": int(stats.get('Total Trades', 0))
            })
            results.append(res)

        return results

    def _generate_signals_vectorized(self, strategy: BaseStrategy, df: pd.DataFrame) -> pd.Series:
        """
        Generic vectorized signal generator using the strategy's logic.
        Refactored to avoid per-bar loops if possible.
        """
        # If the strategy provides a vectorized method, use it
        if hasattr(strategy, 'generate_signals'):
            return strategy.generate_signals(df)
            
        # Fallback: Many our strategies use standard patterns.
        # We'll implement a basic one that calls check_buy_signal in a loop if needed,
        # but encourage strategy authors to implement a vectorized version.
        
        # For now, let's try to be smart. If we can't vectorize, we loop.
        # Note: Optimization is usually done on daily/hourly data, so loops aren't fatal.
        
        signals = pd.Series(index=df.index, data=False)
        for i in range(len(df)):
             if strategy.check_buy_signal(df, i):
                 signals.iloc[i] = True
        return signals
