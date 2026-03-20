"""
Trend Rider 4h V2 optimizer.

Grid search on entry filters + exit params to find more frequent
trading setups while maintaining good returns.

Usage:
    cd backend
    python -u tune_4h_v2.py
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
TIMEFRAME = "4h"
INITIAL_CAPITAL = 1_000_000
FEES = 0.0005
MIN_TRADES = 10  # 4h는 매매 빈도가 낮으므로 최소 거래 수 낮게

END_DATE = "2026-03-17"
START_DATE = "2023-03-17"

# Exit grids
TRAILING_SL_GRID = [0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10]
FIXED_SL_GRID = [0.03, 0.04, 0.05, 0.06]
FIXED_TP_GRID = [0.06, 0.08, 0.10, 0.15, 0.20]

# ── Entry param grid (진입 조건 완화 탐색) ─────────────────────

TREND_RIDER_4H_GRID = {
    # 공통 필터 완화
    "filter_adx_min": [0, 10, 15, 20],           # 0 = ADX 필터 제거
    "filter_volume_min": [0, 0.7, 1.0],           # 0 = 거래량 필터 제거
    "filter_rsi_max": [75, 80, 85],               # RSI 과열 상한 완화
    "filter_close_gt_ema20": [True, False],        # 가격>EMA20 필터 ON/OFF
    "filter_macd_gt_signal": [True, False],        # MACD>Signal 필터 ON/OFF
}


def fetch_all_data(db) -> dict:
    """Fetch OHLCV data for all symbols once."""
    fetcher = DataFetcher()
    base_strategy = get_strategy("trend_rider_4h_v2")
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


def build_portfolio_frames(data: dict) -> pd.DataFrame:
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


def generate_signals_for_symbol(df_indexed: pd.DataFrame,
                                entry_params: dict) -> list:
    """Generate buy signals for a single symbol with given filter params."""
    strategy = get_strategy("trend_rider_4h_v2")

    # Apply filter overrides
    for k, v in entry_params.items():
        setattr(strategy, k, v)

    return [
        strategy.check_buy_signal(df_indexed, idx)
        for idx in range(len(df_indexed))
    ]


def generate_multi_symbol_entries(data: dict, close_df: pd.DataFrame,
                                  entry_params: dict) -> pd.DataFrame:
    """Generate entries across all symbols, shift by 1 bar."""
    entries_df = pd.DataFrame(index=close_df.index)

    for symbol, d in data.items():
        signals = generate_signals_for_symbol(d["df_indexed"].copy(), entry_params)
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
    for sl in TRAILING_SL_GRID:
        combos.append({"sl": sl, "tp": None, "trailing": True})
    for sl, tp in itertools.product(FIXED_SL_GRID, FIXED_TP_GRID):
        combos.append({"sl": sl, "tp": tp, "trailing": False})
    return combos


def entry_param_combos(grid: dict) -> list:
    """Generate all combinations from a grid dict."""
    keys = list(grid.keys())
    values = list(grid.values())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def print_top_results(results: list, n: int = 15):
    """Print TOP N results sorted by total_return."""
    if not results:
        log("  No valid results")
        return

    results.sort(key=lambda x: x["total_return"], reverse=True)

    log(f"\n  {'─'*100}")
    log(f"  TOP {n} by total_return")
    log(f"  {'─'*100}")

    for rank, r in enumerate(results[:n], 1):
        mode = "TRAIL" if r.get("trailing") else "FIXED"
        sl_str = f"SL={r['sl']*100:.1f}%"
        tp_str = f"TP={r['tp']*100:.1f}%" if r.get("tp") else "TP=None"
        params_str = ""
        for k, v in r.get("entry_params", {}).items():
            if isinstance(v, bool):
                params_str += f" {k}={'Y' if v else 'N'}"
            elif isinstance(v, float):
                params_str += f" {k}={v:.2f}"
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

    # Best by risk-adjusted
    by_risk = sorted(results, key=lambda x: x["risk_adjusted"], reverse=True)
    log(f"\n  TOP 5 by RISK-ADJUSTED (Return/DD):")
    for rank, r in enumerate(by_risk[:5], 1):
        mode = "TRAIL" if r.get("trailing") else "FIXED"
        sl_str = f"SL={r['sl']*100:.1f}%"
        tp_str = f"TP={r['tp']*100:.1f}%" if r.get("tp") else "TP=None"
        params_str = ""
        for k, v in r.get("entry_params", {}).items():
            if isinstance(v, bool):
                params_str += f" {k}={'Y' if v else 'N'}"
            elif isinstance(v, float):
                params_str += f" {k}={v:.2f}"
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

    # Best by trade count (매매 빈도 중시)
    by_trades = sorted(results, key=lambda x: (-x["total_trades"], -x["total_return"]))
    log(f"\n  TOP 5 by TRADE COUNT (매매 빈도 우선):")
    for rank, r in enumerate(by_trades[:5], 1):
        mode = "TRAIL" if r.get("trailing") else "FIXED"
        sl_str = f"SL={r['sl']*100:.1f}%"
        tp_str = f"TP={r['tp']*100:.1f}%" if r.get("tp") else "TP=None"
        params_str = ""
        for k, v in r.get("entry_params", {}).items():
            if isinstance(v, bool):
                params_str += f" {k}={'Y' if v else 'N'}"
            elif isinstance(v, float):
                params_str += f" {k}={v:.2f}"
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


def run_baseline(data: dict, close_df: pd.DataFrame):
    """Run current V1 and V2 defaults as baseline."""
    log(f"\n{'='*80}")
    log(f"  BASELINE: Current defaults")
    log(f"{'='*80}")

    for sname in ["trend_rider_4h_v1", "trend_rider_4h_v2"]:
        strategy = get_strategy(sname)
        entries_df = generate_multi_symbol_entries(data, close_df, {})
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
    e_combos = entry_param_combos(TREND_RIDER_4H_GRID)
    exits = exit_combos()
    total = len(e_combos) * len(exits)

    log("=" * 80)
    log("  Trend Rider 4h V2 Optimizer")
    log(f"  Symbols: {', '.join(SYMBOLS)}")
    log(f"  Period: {START_DATE} ~ {END_DATE} (3년)")
    log(f"  Capital: {INITIAL_CAPITAL:,} | Fees: {FEES*100:.2f}% | Min trades: {MIN_TRADES}")
    log(f"  Entry combos: {len(e_combos)} | Exit combos: {len(exits)} | Total: {total}")
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

        # 2. Grid search
        log(f"\n{'='*80}")
        log(f"  GRID SEARCH: trend_rider_4h_v2")
        log(f"{'='*80}")

        results = []
        count = 0
        t0 = time.time()

        for ep in e_combos:
            entries_df = generate_multi_symbol_entries(data, close_df, ep)
            n_signals = int(entries_df.sum().sum())

            for ex in exits:
                count += 1
                if count % 50 == 0 or count == 1:
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

        print_top_results(results)

    finally:
        db.close()

    log(f"\n{'='*80}")
    log("  Done.")


if __name__ == "__main__":
    main()
