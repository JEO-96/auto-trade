"""
Comprehensive 15m strategy optimizer.

Tests all 4 strategies (scalper, quick_swing, multi_signal, trend_follower)
across multiple coins with grid search on entry params + exit params.

Signals are cached per unique entry-param combo so SL/TP/trailing
variations reuse cached signals (only the vectorbt portfolio changes).

Usage:
    cd backend
    python -u tune_15m.py
"""

import sys
import os
import time
import itertools
import logging
import warnings
from datetime import datetime, timedelta
from copy import deepcopy

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import pandas as pd
import numpy as np
import vectorbt as vbt

from core.strategy import get_strategy
from core.data_fetcher import DataFetcher
import database

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def log(msg: str):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


# ── Configuration ──────────────────────────────────────────────

SYMBOLS = ["BTC/KRW", "ETH/KRW", "XRP/KRW", "SOL/KRW"]
TIMEFRAME = "15m"
INITIAL_CAPITAL = 1_000_000
FEES = 0.0005
MIN_TRADES = 30

END_DATE = datetime.now().strftime("%Y-%m-%d")
START_DATE = (datetime.now() - timedelta(days=2 * 365)).strftime("%Y-%m-%d")

# Exit grids
TRAILING_SL_GRID = [0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.025, 0.030, 0.035, 0.040]
FIXED_SL_GRID = [0.008, 0.010, 0.012, 0.015, 0.020]
FIXED_TP_GRID = [0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050]

# ── Strategy-specific entry param grids ─────────────────────────

SCALPER_GRID = {
    "rsi_threshold": [35, 40, 45, 50, 55],
    "adx_threshold": [12, 15, 18, 22, 25],
    "volume_multiplier": [0.8, 1.0, 1.2],
    "rsi_upper_limit": [70, 75, 80],
}

QUICK_SWING_GRID = {
    "rsi_bounce_threshold": [40, 45, 48, 52, 55],  # rsi_prev < X
    "adx_threshold": [12, 15, 18, 22, 25],
    "rsi_upper_limit": [70, 74, 78],
}

MULTI_SIGNAL_GRID = {
    "breakout_adx_min": [18, 22, 25, 28],
    "trend_rider_adx_min": [22, 25, 30, 35],
    "rsi_threshold": [45, 50, 55, 60],
    "volume_multiplier": [1.0, 1.2, 1.3, 1.5],
    "rsi_upper_limit": [72, 76, 80],
}

TREND_FOLLOWER_GRID = {
    "adx_threshold": [15, 18, 20, 22, 25],
    "rsi_lower": [40, 45, 50],
    "rsi_upper": [68, 72, 76, 80],
    "ema_proximity_pct": [0.003, 0.005, 0.008, 0.010],
}


def fetch_all_data(db) -> dict:
    """Fetch OHLCV data for all symbols once."""
    fetcher = DataFetcher()
    base_strategy = get_strategy("scalper_15m")
    data = {}

    for symbol in SYMBOLS:
        log(f"  Fetching {symbol} {TIMEFRAME} ({START_DATE} ~ {END_DATE})...")
        df = fetcher.fetch_ohlcv(
            symbol, TIMEFRAME, limit=None,
            start_date=START_DATE, end_date=END_DATE, db=db,
        )
        if df is None or len(df) == 0:
            log(f"  WARNING: No data for {symbol}, skipping")
            continue

        log(f"    {len(df)} bars fetched")
        df = base_strategy.apply_indicators(df)
        df_indexed = df.set_index("timestamp")
        data[symbol] = {"df": df, "df_indexed": df_indexed}

    return data


def build_portfolio_frames(data: dict) -> tuple:
    """Build aligned close_df from multi-symbol data."""
    all_timestamps = sorted(set().union(
        *(d["df_indexed"].index.tolist() for d in data.values())
    ))
    close_df = pd.DataFrame(index=all_timestamps)
    for symbol, d in data.items():
        close_df[symbol] = d["df_indexed"]["close"]
    close_df.ffill(inplace=True)
    close_df.bfill(inplace=True)
    close_df.dropna(how="any", inplace=True)
    return close_df


def generate_signals_for_symbol(strategy_name: str, df_indexed: pd.DataFrame,
                                entry_params: dict) -> list:
    """Generate buy signals for a single symbol with given params."""
    strategy = get_strategy(strategy_name)
    for k, v in entry_params.items():
        setattr(strategy, k, v)

    # For multi_signal, need to re-apply EMA_100
    if strategy_name == "multi_signal_15m":
        ema100 = df_indexed.ta.ema(length=100) if hasattr(df_indexed, 'ta') else None
        if ema100 is not None:
            if hasattr(ema100, 'iloc') and ema100.ndim > 1:
                df_indexed['EMA_100'] = ema100.iloc[:, 0]
            else:
                df_indexed['EMA_100'] = ema100

    return [
        strategy.check_buy_signal(df_indexed, idx)
        for idx in range(len(df_indexed))
    ]


def generate_multi_symbol_entries(strategy_name: str, data: dict,
                                  close_df: pd.DataFrame,
                                  entry_params: dict) -> pd.DataFrame:
    """Generate entries across all symbols, shift by 1 bar."""
    entries_df = pd.DataFrame(index=close_df.index)

    for symbol, d in data.items():
        signals = generate_signals_for_symbol(
            strategy_name, d["df_indexed"].copy(), entry_params
        )
        sig_series = pd.Series(signals, index=d["df_indexed"].index)
        entries_df[symbol] = sig_series

    entries_df = entries_df.reindex(close_df.index).fillna(False)
    entries_df = entries_df.shift(1).fillna(False).astype(bool)
    return entries_df


def run_portfolio(close_df: pd.DataFrame, entries_df: pd.DataFrame,
                  sl_pct: float, tp_pct: float | None, trailing: bool) -> dict | None:
    """Run vectorbt portfolio and extract metrics."""
    pf_kwargs = dict(
        close=close_df,
        entries=entries_df,
        exits=None,
        init_cash=INITIAL_CAPITAL,
        fees=FEES,
        freq=TIMEFRAME,
        cash_sharing=True,
        group_by=True,
    )
    if trailing:
        pf_kwargs["sl_stop"] = sl_pct
        pf_kwargs["sl_trail"] = True
    else:
        pf_kwargs["sl_stop"] = sl_pct
        if tp_pct is not None:
            pf_kwargs["tp_stop"] = tp_pct

    try:
        portfolio = vbt.Portfolio.from_signals(**pf_kwargs)
    except Exception:
        return None

    try:
        total_trades = int(portfolio.trades.count())
    except (TypeError, AttributeError):
        try:
            total_trades = len(portfolio.trades.records)
        except Exception:
            total_trades = 0

    if total_trades < MIN_TRADES:
        return None

    final_val = float(portfolio.final_value())
    total_return = (final_val / INITIAL_CAPITAL - 1) * 100

    try:
        max_dd = float(portfolio.max_drawdown()) * 100
    except Exception:
        max_dd = 0.0

    try:
        win_rate = float(portfolio.trades.win_rate()) * 100
    except Exception:
        win_rate = 0.0

    # Sharpe-like metric: return / max_dd (higher is better)
    risk_adj = total_return / abs(max_dd) if max_dd != 0 else 0.0

    return {
        "total_return": round(total_return, 2),
        "total_trades": total_trades,
        "max_drawdown": round(max_dd, 2),
        "win_rate": round(win_rate, 2),
        "risk_adjusted": round(risk_adj, 2),
        "final_capital": round(final_val, 0),
    }


def exit_combos() -> list:
    """All SL/TP/trailing combos to test."""
    combos = []
    # Trailing mode (our primary mode for 15m)
    for sl in TRAILING_SL_GRID:
        combos.append({"sl": sl, "tp": None, "trailing": True})
    # Fixed SL/TP mode
    for sl, tp in itertools.product(FIXED_SL_GRID, FIXED_TP_GRID):
        combos.append({"sl": sl, "tp": tp, "trailing": False})
    return combos


def entry_param_combos(grid: dict) -> list:
    """Generate all combinations from a grid dict."""
    keys = list(grid.keys())
    values = list(grid.values())
    combos = []
    for combo in itertools.product(*values):
        combos.append(dict(zip(keys, combo)))
    return combos


def print_top_results(results: list, strategy_name: str, n: int = 15):
    """Print TOP N results sorted by total_return."""
    if not results:
        log(f"  {strategy_name}: No valid results")
        return

    # Sort by risk_adjusted score (return / drawdown ratio)
    results.sort(key=lambda x: x["total_return"], reverse=True)

    log(f"\n  {'─'*90}")
    log(f"  TOP {n} by total_return ({strategy_name})")
    log(f"  {'─'*90}")

    for rank, r in enumerate(results[:n], 1):
        mode = "TRAIL" if r.get("trailing") else "FIXED"
        sl_str = f"SL={r['sl']*100:.1f}%"
        tp_str = f"TP={r['tp']*100:.1f}%" if r.get("tp") else "TP=None"
        params_str = ""
        for k, v in r.get("entry_params", {}).items():
            if isinstance(v, float):
                params_str += f" {k}={v:.3f}"
            else:
                params_str += f" {k}={v}"
        log(
            f"  #{rank:2d} | {mode:5s} {sl_str:8s} {tp_str:10s}"
            f" | Ret={r['total_return']:+8.1f}%"
            f" | Trades={r['total_trades']:4d}"
            f" | WR={r['win_rate']:5.1f}%"
            f" | DD={r['max_drawdown']:6.1f}%"
            f" | R/DD={r['risk_adjusted']:5.2f}"
            f" |{params_str}"
        )

    # Also show best by risk-adjusted
    by_risk = sorted(results, key=lambda x: x["risk_adjusted"], reverse=True)
    log(f"\n  TOP 5 by RISK-ADJUSTED (Return/DD):")
    for rank, r in enumerate(by_risk[:5], 1):
        mode = "TRAIL" if r.get("trailing") else "FIXED"
        sl_str = f"SL={r['sl']*100:.1f}%"
        tp_str = f"TP={r['tp']*100:.1f}%" if r.get("tp") else "TP=None"
        params_str = ""
        for k, v in r.get("entry_params", {}).items():
            if isinstance(v, float):
                params_str += f" {k}={v:.3f}"
            else:
                params_str += f" {k}={v}"
        log(
            f"  #{rank:2d} | {mode:5s} {sl_str:8s} {tp_str:10s}"
            f" | Ret={r['total_return']:+8.1f}%"
            f" | WR={r['win_rate']:5.1f}%"
            f" | DD={r['max_drawdown']:6.1f}%"
            f" | R/DD={r['risk_adjusted']:5.2f}"
            f" |{params_str}"
        )


def grid_search_strategy(strategy_name: str, data: dict, close_df: pd.DataFrame,
                         entry_grid: dict, max_entry_combos: int = 200) -> list:
    """Generic grid search for any strategy."""
    log(f"\n{'='*80}")
    log(f"  GRID SEARCH: {strategy_name}")
    log(f"{'='*80}")

    e_combos = entry_param_combos(entry_grid)
    if len(e_combos) > max_entry_combos:
        log(f"  WARNING: {len(e_combos)} entry combos > {max_entry_combos}, sampling...")
        import random
        random.seed(42)
        e_combos = random.sample(e_combos, max_entry_combos)

    exits = exit_combos()
    total = len(e_combos) * len(exits)
    log(f"  Entry combos: {len(e_combos)}")
    log(f"  Exit combos: {len(exits)}")
    log(f"  Total combinations: {total}")

    results = []
    count = 0
    t0 = time.time()

    for ep in e_combos:
        # Generate signals once per entry combo
        entries_df = generate_multi_symbol_entries(
            strategy_name, data, close_df, ep
        )
        n_signals = int(entries_df.sum().sum())

        for ex in exits:
            count += 1
            if count % 100 == 0 or count == 1:
                elapsed = time.time() - t0
                rate = count / elapsed if elapsed > 0 else 0
                eta = (total - count) / rate if rate > 0 else 0
                log(f"  [{count}/{total}] {elapsed:.0f}s elapsed, ~{eta:.0f}s remaining")

            if n_signals < MIN_TRADES:
                continue

            metrics = run_portfolio(close_df, entries_df,
                                    ex["sl"], ex["tp"], ex["trailing"])
            if metrics:
                metrics.update({
                    "entry_params": ep,
                    "sl": ex["sl"],
                    "tp": ex["tp"],
                    "trailing": ex["trailing"],
                })
                results.append(metrics)

    elapsed = time.time() - t0
    log(f"\n  Completed {count} combinations in {elapsed:.1f}s")
    log(f"  Valid results (>={MIN_TRADES} trades): {len(results)}")

    print_top_results(results, strategy_name)
    return results


def run_baseline(data: dict, close_df: pd.DataFrame):
    """Run current strategy defaults as baseline."""
    log(f"\n{'='*80}")
    log(f"  BASELINE: Current strategy defaults")
    log(f"{'='*80}")

    strategies = ["scalper_15m", "quick_swing_15m", "multi_signal_15m", "trend_follower_15m"]

    for sname in strategies:
        strategy = get_strategy(sname)
        entries_df = generate_multi_symbol_entries(sname, data, close_df, {})
        n_signals = int(entries_df.sum().sum())

        sl = strategy.backtest_sl_pct
        tp = strategy.backtest_tp_pct
        trailing = getattr(strategy, 'backtest_trailing', False)

        metrics = run_portfolio(close_df, entries_df, sl, tp, trailing)

        mode = "TRAIL" if trailing else "FIXED"
        sl_str = f"SL={sl*100:.1f}%" if sl else "SL=None"
        tp_str = f"TP={tp*100:.1f}%" if tp else "TP=None"

        if metrics:
            log(
                f"  {sname:25s} | {mode:5s} {sl_str:8s} {tp_str:10s}"
                f" | Signals={n_signals:4d}"
                f" | Ret={metrics['total_return']:+8.1f}%"
                f" | Trades={metrics['total_trades']:4d}"
                f" | WR={metrics['win_rate']:5.1f}%"
                f" | DD={metrics['max_drawdown']:6.1f}%"
                f" | R/DD={metrics['risk_adjusted']:5.2f}"
            )
        else:
            log(f"  {sname:25s} | Signals={n_signals:4d} | INSUFFICIENT TRADES (<{MIN_TRADES})")


def main():
    log("=" * 80)
    log("  15m Strategy Comprehensive Optimizer")
    log(f"  Symbols: {', '.join(SYMBOLS)}")
    log(f"  Period: {START_DATE} ~ {END_DATE}")
    log(f"  Capital: {INITIAL_CAPITAL:,} | Fees: {FEES*100:.2f}% | Min trades: {MIN_TRADES}")
    log("=" * 80)

    db = database.SessionLocal()
    try:
        data = fetch_all_data(db)
        if not data:
            log("ERROR: No data fetched for any symbol")
            return

        close_df = build_portfolio_frames(data)
        log(f"\n  Aligned portfolio: {len(close_df)} bars, {len(close_df.columns)} symbols")

        # 1. Baseline
        run_baseline(data, close_df)

        # 2. Grid search each strategy
        scalper_results = grid_search_strategy(
            "scalper_15m", data, close_df, SCALPER_GRID
        )

        quick_swing_results = grid_search_strategy(
            "quick_swing_15m", data, close_df, QUICK_SWING_GRID
        )

        multi_signal_results = grid_search_strategy(
            "multi_signal_15m", data, close_df, MULTI_SIGNAL_GRID
        )

        trend_follower_results = grid_search_strategy(
            "trend_follower_15m", data, close_df, TREND_FOLLOWER_GRID
        )

        # 3. Summary
        log(f"\n{'='*80}")
        log("  FINAL SUMMARY — BEST PARAMS PER STRATEGY")
        log(f"{'='*80}")

        for name, results in [
            ("scalper_15m", scalper_results),
            ("quick_swing_15m", quick_swing_results),
            ("multi_signal_15m", multi_signal_results),
            ("trend_follower_15m", trend_follower_results),
        ]:
            if not results:
                log(f"\n  {name}: No valid results")
                continue

            # Best by return
            by_return = sorted(results, key=lambda x: x["total_return"], reverse=True)[0]
            # Best by risk-adjusted
            by_risk = sorted(results, key=lambda x: x["risk_adjusted"], reverse=True)[0]

            log(f"\n  {name}:")
            log(f"    BEST RETURN:")
            mode = "TRAIL" if by_return.get("trailing") else "FIXED"
            log(f"      Mode: {mode} | SL: {by_return['sl']*100:.1f}%"
                f" | TP: {by_return['tp']*100:.1f}%" if by_return.get("tp") else
                f"      Mode: {mode} | SL: {by_return['sl']*100:.1f}% | TP: None")
            log(f"      Return: {by_return['total_return']:+.1f}%"
                f" | Trades: {by_return['total_trades']}"
                f" | WR: {by_return['win_rate']:.1f}%"
                f" | DD: {by_return['max_drawdown']:.1f}%")
            log(f"      Entry params: {by_return['entry_params']}")

            log(f"    BEST RISK-ADJUSTED (R/DD):")
            mode = "TRAIL" if by_risk.get("trailing") else "FIXED"
            log(f"      Mode: {mode} | SL: {by_risk['sl']*100:.1f}%"
                f" | TP: {by_risk['tp']*100:.1f}%" if by_risk.get("tp") else
                f"      Mode: {mode} | SL: {by_risk['sl']*100:.1f}% | TP: None")
            log(f"      Return: {by_risk['total_return']:+.1f}%"
                f" | Trades: {by_risk['total_trades']}"
                f" | WR: {by_risk['win_rate']:.1f}%"
                f" | DD: {by_risk['max_drawdown']:.1f}%"
                f" | R/DD: {by_risk['risk_adjusted']:.2f}")
            log(f"      Entry params: {by_risk['entry_params']}")

    finally:
        db.close()

    log(f"\n{'='*80}")
    log("  Done.")


if __name__ == "__main__":
    main()
