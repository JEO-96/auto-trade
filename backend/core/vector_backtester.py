import logging
import traceback
import pandas as pd
import numpy as np
import vectorbt as vbt
from core.data_fetcher import DataFetcher
from core.strategy import get_strategy
from core import config
import database
import uuid
import threading
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

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
            # Create a thread-local DB session for background execution.
            # The request-scoped session must NOT be used across threads.
            db = database.SessionLocal()
            kwargs["db"] = db
            try:
                result = self._run_backtest(symbols, task_id=task_id, **kwargs)
            finally:
                db.close()

            backtest_tasks[task_id]["status"] = "completed"
            backtest_tasks[task_id]["progress"] = 100.0
            backtest_tasks[task_id]["result"] = result
            backtest_tasks[task_id]["message"] = "Backtest completed."
            backtest_tasks[task_id]["completed_at"] = time.time()
        except Exception as e:
            logger.error("Async backtest error: %s", e)
            logger.debug(traceback.format_exc())
            backtest_tasks[task_id]["status"] = "failed"
            backtest_tasks[task_id]["message"] = str(e)

    def run(self, symbol="BTC/KRW", timeframe="1h", limit=1000,
            initial_capital=1000000.0, start_date=None, end_date=None,
            db=None, task_id=None, fees=0.0005, custom_params=None):
        return self._run_backtest(
            [symbol], timeframe=timeframe, limit=limit,
            initial_capital=initial_capital, start_date=start_date,
            end_date=end_date, db=db, task_id=task_id, fees=fees,
            custom_params=custom_params,
        )

    def run_portfolio(self, symbols: list, timeframe="1h", limit=1000,
                      initial_capital=1000000.0, start_date=None,
                      end_date=None, db=None, task_id=None, fees=0.0005,
                      custom_params=None):
        return self._run_backtest(
            symbols, timeframe=timeframe, limit=limit,
            initial_capital=initial_capital, start_date=start_date,
            end_date=end_date, db=db, task_id=task_id, fees=fees,
            custom_params=custom_params,
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
                      end_date=None, db=None, task_id=None, fees=0.0005,
                      custom_params=None):
        """Core backtest execution for both single and multi-asset."""
        logger.info("--- [VectorBacktest] Symbols: %s ---", symbols)

        if not symbols:
            return {"status": "error", "message": "No symbols provided."}

        # 커스텀 파라미터를 전략 인스턴스에 적용
        if custom_params:
            # 진입 신호 파라미터 (값 덮어쓰기)
            param_map = {
                'rsi_period': 'rsi_period',
                'rsi_threshold': 'rsi_threshold',
                'adx_threshold': 'adx_threshold',
                'volume_multiplier': 'volume_multiplier',
                'macd_fast': 'macd_fast',
                'macd_slow': 'macd_slow',
                'macd_signal': 'macd_signal',
                'rsi_upper_limit': 'rsi_upper_limit',
                'atr_period': 'atr_period',
            }
            for param_key, attr_name in param_map.items():
                val = custom_params.get(param_key)
                if val is not None and hasattr(self.strategy, attr_name):
                    setattr(self.strategy, attr_name, val)

            # 조건 비활성화: 해당 필터의 threshold를 극단값으로 설정하여 항상 통과
            if custom_params.get('use_rsi_filter') is False:
                self.strategy.rsi_threshold = 0.0  # RSI > 0 → 항상 통과
                if hasattr(self.strategy, 'rsi_upper_limit'):
                    self.strategy.rsi_upper_limit = 100.0
            if custom_params.get('use_adx_filter') is False:
                self.strategy.adx_threshold = 0.0  # ADX > 0 → 항상 통과
            if custom_params.get('use_volume_filter') is False:
                self.strategy.volume_multiplier = 0.0  # vol > 0 → 항상 통과
            if custom_params.get('use_macd_filter') is False:
                # MACD 필터 비활성화는 전략마다 다르지만 fast=slow로 설정하면 크로스가 무의미
                self.strategy.macd_fast = self.strategy.macd_slow

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
        # Forward-fill then back-fill to handle leading NaN for symbols
        # that started trading later than others in the portfolio
        close_df.ffill(inplace=True)
        close_df.bfill(inplace=True)

        # Drop any rows that still have NaN (should not happen after ffill+bfill,
        # but guard against completely empty columns)
        nan_rows = close_df.isna().any(axis=1)
        if nan_rows.any():
            close_df = close_df[~nan_rows]
            entries_df = entries_df[~nan_rows]

        if close_df.empty:
            return {"status": "error", "message": "No valid price data after alignment."}

        # Shift entries by 1 bar to prevent look-ahead bias
        # Signal fires on bar N, execution happens on bar N+1
        entries_df = entries_df.shift(1).fillna(False)

        # Ensure entries_df is boolean type (shift can convert to object)
        entries_df = entries_df.astype(bool)

        self._update_progress(
            task_id, 70.0,
            f"Executing vectorbt simulation for {len(ohlcv_data)} assets...",
        )

        # 3. Execute Vectorized Portfolio (커스텀 파라미터 우선, 없으면 전략 기본값)
        if custom_params and custom_params.get('trailing') is not None:
            use_trailing = custom_params['trailing']
        else:
            use_trailing = getattr(self.strategy, 'backtest_trailing', False)

        if custom_params and custom_params.get('sl_pct') is not None:
            sl_pct = custom_params['sl_pct']
        else:
            sl_pct = getattr(self.strategy, 'backtest_sl_pct', 0.015)

        if use_trailing:
            tp_pct = None  # 트레일링 모드에서는 TP 없음
        elif custom_params and custom_params.get('tp_pct') is not None:
            tp_pct = custom_params['tp_pct']
        else:
            tp_pct = getattr(self.strategy, 'backtest_tp_pct', 0.03)

        pf_kwargs = dict(
            close=close_df,
            entries=entries_df,
            exits=None,
            init_cash=initial_capital,
            fees=fees,
            freq=timeframe,
            cash_sharing=True,
            group_by=True,
        )
        if use_trailing:
            # 트레일링 스탑: 고점 대비 sl_pct 하락 시 청산, TP 없음
            pf_kwargs['sl_stop'] = sl_pct
            pf_kwargs['sl_trail'] = True
            # tp_stop은 설정하지 않음 (수익 제한 없이 추세 추종)
        else:
            if sl_pct is not None:
                pf_kwargs['sl_stop'] = sl_pct
            if tp_pct is not None:
                pf_kwargs['tp_stop'] = tp_pct

        portfolio = vbt.Portfolio.from_signals(**pf_kwargs)

        self._update_progress(task_id, 90.0, "Formatting results...")

        # 4. Format Output
        formatted_trades = self._format_trades(portfolio, symbols, initial_capital, close_df)

        # 5. Extract Equity Curve
        equity_series = portfolio.value()
        equity_curve = [
            {"time": str(ts), "value": float(val)}
            for ts, val in equity_series.items()
        ]

        # 6. Extract price change rates for charting (% change from first price)
        price_changes = {}
        for symbol in close_df.columns:
            series = close_df[symbol].dropna()
            if len(series) > 0:
                first_price = series.iloc[0]
                price_changes[symbol] = [
                    {"time": str(ts), "value": round(((val / first_price) - 1) * 100, 4)}
                    for ts, val in series.items()
                ]

        # 7. Fetch BTC benchmark if not already in symbols
        btc_benchmark = None
        if "BTC/KRW" not in close_df.columns:
            try:
                btc_df = self.fetcher.fetch_ohlcv(
                    "BTC/KRW", timeframe, limit=limit,
                    start_date=start_date, end_date=end_date, db=db,
                )
                if btc_df is not None and len(btc_df) > 0:
                    btc_indexed = btc_df.set_index('timestamp')['close']
                    # Align to same time range
                    common_idx = close_df.index.intersection(btc_indexed.index)
                    if len(common_idx) > 0:
                        btc_aligned = btc_indexed.loc[common_idx]
                        first_btc = btc_aligned.iloc[0]
                        btc_benchmark = [
                            {"time": str(ts), "value": round(((val / first_btc) - 1) * 100, 4)}
                            for ts, val in btc_aligned.items()
                        ]
            except Exception as e:
                logger.warning("Failed to fetch BTC benchmark: %s", e)

        # Safely get total trade count across different vectorbt versions
        try:
            total_trades = int(portfolio.trades.count())
        except (TypeError, AttributeError):
            try:
                total_trades = len(portfolio.trades.records)
            except Exception:
                total_trades = len(formatted_trades) // 2

        return {
            "status": "success",
            "initial_capital": float(initial_capital),
            "final_capital": float(portfolio.final_value()),
            "total_trades": total_trades,
            "trades": formatted_trades,
            "equity_curve": equity_curve,
            "price_changes": price_changes,
            "btc_benchmark": btc_benchmark,
        }

    # ------------------------------------------------------------------
    # Trade formatting -- version-agnostic column resolution
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
        try:
            vbt_trades = portfolio.trades.records_readable
        except Exception as e:
            logger.warning("Could not read trades from portfolio: %s", e)
            return []

        if vbt_trades.empty:
            return []

        cols = vbt_trades.columns.tolist()
        logger.debug("vectorbt trades columns: %s", cols)

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

            # Guard against NaN prices
            if pd.isna(entry_price) or pd.isna(exit_price):
                continue

            # PnL
            pnl_val = float(t[pnl_col]) if pnl_col and pd.notna(t.get(pnl_col)) else 0.0

            # Timestamps -- use column if available, otherwise reconstruct from index
            if entry_ts_col and entry_ts_col in t.index:
                entry_time = str(t[entry_ts_col])
            elif entry_idx_col and entry_idx_col in t.index:
                idx_val = int(t[entry_idx_col])
                entry_time = str(close_df.index[idx_val]) if 0 <= idx_val < len(close_df.index) else "N/A"
            else:
                entry_time = "N/A"

            if exit_ts_col and exit_ts_col in t.index:
                exit_time = str(t[exit_ts_col])
            elif exit_idx_col and exit_idx_col in t.index:
                idx_val = int(t[exit_idx_col])
                exit_time = str(close_df.index[idx_val]) if 0 <= idx_val < len(close_df.index) else "N/A"
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
