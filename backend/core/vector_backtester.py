import pandas as pd
import numpy as np
import vectorbt as vbt
from core.data_fetcher import DataFetcher
from core.strategy import get_strategy
from core import config
import uuid
import threading
import time
from typing import Dict, Any, Optional

# Global storage for backtest tasks
# task_id -> {status, progress, result}
backtest_tasks: Dict[str, Dict[str, Any]] = {}


class VectorBacktester:
    """
    High-performance backtesting engine using vectorbt.
    Handles vectorized operations for maximum speed.
    """
    def __init__(self, strategy_name="james_basic"):
        self.fetcher = DataFetcher()
        self.strategy = get_strategy(strategy_name)

    def start_async_backtest(self, symbols: list, is_portfolio: bool, **kwargs) -> str:
        """Starts backtest in a background thread and returns a task_id."""
        task_id = str(uuid.uuid4())
        backtest_tasks[task_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "Initializing data fetch...",
            "result": None,
        }

        thread = threading.Thread(
            target=self._run_task,
            args=(task_id, symbols, is_portfolio),
            kwargs=kwargs,
        )
        thread.start()
        return task_id

    def _run_task(self, task_id: str, symbols: list, is_portfolio: bool, **kwargs):
        try:
            result = self._run_backtest(symbols, task_id=task_id, **kwargs)

            backtest_tasks[task_id]["status"] = "completed"
            backtest_tasks[task_id]["progress"] = 100.0
            backtest_tasks[task_id]["result"] = result
            backtest_tasks[task_id]["message"] = "Backtest completed."
            backtest_tasks[task_id]["completed_at"] = time.time()
        except Exception as e:
            print(f"Async backtest error: {e}")
            backtest_tasks[task_id]["status"] = "failed"
            backtest_tasks[task_id]["message"] = str(e)

    def run(self, symbol="BTC/KRW", timeframe="1h", limit=1000,
            initial_capital=1000000.0, start_date=None, end_date=None,
            db=None, task_id=None):
        return self._run_backtest(
            [symbol], timeframe=timeframe, limit=limit,
            initial_capital=initial_capital, start_date=start_date,
            end_date=end_date, db=db, task_id=task_id,
        )

    def run_portfolio(self, symbols: list, timeframe="1h", limit=1000,
                      initial_capital=1000000.0, start_date=None,
                      end_date=None, db=None, task_id=None):
        return self._run_backtest(
            symbols, timeframe=timeframe, limit=limit,
            initial_capital=initial_capital, start_date=start_date,
            end_date=end_date, db=db, task_id=task_id,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_progress(self, task_id: Optional[str], progress: float, message: str):
        """Helper to update task progress if task_id is available."""
        if task_id and task_id in backtest_tasks:
            backtest_tasks[task_id]["progress"] = progress
            backtest_tasks[task_id]["message"] = message

    def _run_backtest(self, symbols: list, timeframe="1h", limit=1000,
                      initial_capital=1000000.0, start_date=None,
                      end_date=None, db=None, task_id=None):
        """Core backtest execution for both single and multi-asset."""
        print(f"--- [VectorBacktest] Symbols: {symbols} ---")

        # 1. Fetch and align data
        ohlcv_data = {}
        total_symbols = len(symbols)

        for i, symbol in enumerate(symbols):
            progress = (i / total_symbols) * 40.0
            self._update_progress(task_id, progress,
                                  f"Fetching data for {symbol} ({i+1}/{total_symbols})...")

            df = self.fetcher.fetch_ohlcv(
                symbol, timeframe, limit=limit,
                start_date=start_date, end_date=end_date, db=db,
            )
            if df is not None and len(df) > 0:
                df = self.strategy.apply_indicators(df)
                ohlcv_data[symbol] = df

        if not ohlcv_data:
            return {"status": "error", "message": "No data fetched for any symbol."}

        self._update_progress(task_id, 50.0, "Aligning data and generating signals...")

        # 2. Build unified close / entries DataFrames
        all_timestamps = sorted(set().union(
            *(df['timestamp'].tolist() for df in ohlcv_data.values())
        ))
        close_df = pd.DataFrame(index=all_timestamps)
        entries_df = pd.DataFrame(index=all_timestamps)

        for symbol, df in ohlcv_data.items():
            df_indexed = df.set_index('timestamp')
            close_df[symbol] = df_indexed['close']

            signals = [
                self.strategy.check_buy_signal(df_indexed, idx)
                for idx in range(len(df_indexed))
            ]
            entries_df[symbol] = pd.Series(signals, index=df_indexed.index)

        entries_df.fillna(False, inplace=True)
        close_df.ffill(inplace=True)

        # Shift entries by 1 bar to prevent look-ahead bias
        # Signal fires on bar N, execution happens on bar N+1
        entries_df = entries_df.shift(1).fillna(False)

        self._update_progress(
            task_id, 70.0,
            f"Executing vectorbt simulation for {len(ohlcv_data)} assets...",
        )

        # 3. Execute Vectorized Portfolio
        portfolio = vbt.Portfolio.from_signals(
            close=close_df,
            entries=entries_df,
            exits=None,
            sl_stop=0.015,
            tp_stop=0.03,
            init_cash=initial_capital,
            fees=0.0005,
            freq=timeframe,
            cash_sharing=True,
            group_by=True,
        )

        self._update_progress(task_id, 90.0, "Formatting results...")

        # 4. Format Output
        formatted_trades = self._format_trades(portfolio, symbols, initial_capital, close_df)
        
        # 5. Extract Equity Curve
        equity_series = portfolio.value()
        equity_curve = [
            {"time": str(ts), "value": float(val)}
            for ts, val in equity_series.items()
        ]

        return {
            "status": "success",
            "initial_capital": float(initial_capital),
            "final_capital": float(portfolio.final_value()),
            "total_trades": int(portfolio.trades.count()) if hasattr(portfolio.trades, 'count') else len(portfolio.trades.records),
            "trades": formatted_trades,
            "equity_curve": equity_curve
        }

    # ------------------------------------------------------------------
    # Trade formatting – version-agnostic column resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_column(columns: list, *candidates: str) -> Optional[str]:
        """
        Return the first column name from *candidates* that exists in *columns*
        (case-insensitive, space-insensitive match).
        """
        norm_map = {c.lower().replace(' ', '').replace('_', ''): c for c in columns}
        for candidate in candidates:
            key = candidate.lower().replace(' ', '').replace('_', '')
            if key in norm_map:
                return norm_map[key]
        return None

    def _format_trades(self, portfolio, symbols: list,
                       initial_capital: float,
                       close_df: pd.DataFrame) -> list:
        """
        Extract trades from vectorbt portfolio in a version-agnostic manner.
        Supports both old (Entry Timestamp) and new (Entry Idx) column layouts.
        """
        vbt_trades = portfolio.trades.records_readable

        if vbt_trades.empty:
            return []

        cols = vbt_trades.columns.tolist()
        print(f"[DEBUG] vectorbt trades columns: {cols}")

        # Resolve column names
        entry_price_col = self._resolve_column(cols, 'Entry Price', 'Avg Entry Price')
        exit_price_col = self._resolve_column(cols, 'Exit Price', 'Avg Exit Price')
        pnl_col = self._resolve_column(cols, 'PnL')
        entry_ts_col = self._resolve_column(cols, 'Entry Timestamp')
        exit_ts_col = self._resolve_column(cols, 'Exit Timestamp')
        entry_idx_col = self._resolve_column(cols, 'Entry Idx', 'Entry Index')
        exit_idx_col = self._resolve_column(cols, 'Exit Idx', 'Exit Index')
        column_col = self._resolve_column(cols, 'Column', 'Col')

        # Determine sort column
        sort_col = entry_ts_col or entry_idx_col or cols[0]

        formatted_trades = []
        current_equity = initial_capital

        for _, t in vbt_trades.sort_values(sort_col).iterrows():
            # Symbol
            symbol_val = t[column_col] if column_col and column_col in t.index else symbols[0]

            # Entry / Exit prices
            entry_price = t[entry_price_col] if entry_price_col else None
            exit_price = t[exit_price_col] if exit_price_col else None

            if entry_price is None or exit_price is None:
                continue

            # PnL
            pnl_val = float(t[pnl_col]) if pnl_col and pd.notna(t.get(pnl_col)) else 0.0

            # Timestamps – use column if available, otherwise reconstruct from index
            if entry_ts_col and entry_ts_col in t.index:
                entry_time = str(t[entry_ts_col])
            elif entry_idx_col and entry_idx_col in t.index:
                idx_val = int(t[entry_idx_col])
                entry_time = str(close_df.index[idx_val]) if idx_val < len(close_df.index) else "N/A"
            else:
                entry_time = "N/A"

            if exit_ts_col and exit_ts_col in t.index:
                exit_time = str(t[exit_ts_col])
            elif exit_idx_col and exit_idx_col in t.index:
                idx_val = int(t[exit_idx_col])
                exit_time = str(close_df.index[idx_val]) if idx_val < len(close_df.index) else "N/A"
            else:
                exit_time = "N/A"

            # Append BUY record
            formatted_trades.append({
                'symbol': str(symbol_val),
                'side': 'BUY',
                'price': float(entry_price),
                'capital': float(current_equity),
                'time': entry_time,
                'reason': 'Vector Entry',
                'pnl': 0.0,
            })

            current_equity += pnl_val

            # Append SELL record
            formatted_trades.append({
                'symbol': str(symbol_val),
                'side': 'SELL',
                'price': float(exit_price),
                'capital': float(current_equity),
                'time': exit_time,
                'reason': 'Vector Exit (SL/TP)',
                'pnl': pnl_val,
            })

        return formatted_trades
