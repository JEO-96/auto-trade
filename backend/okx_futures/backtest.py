"""
OKX 선물 전략 멀티심볼 백테스트

사용법:
    cd backend
    python -m okx_futures.backtest
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from okx_futures.exchange import create_okx_client, fetch_ohlcv
from okx_futures.strategy import SmartTrendFuturesStrategy

# 멀티심볼 대상
# BTC + ETH (4년 검증 완료)
SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
]


def fetch_extended_ohlcv(
    exchange, symbol: str, timeframe: str = "1h", pages: int = 5
) -> pd.DataFrame:
    """페이지네이션으로 OHLCV 수집"""
    all_bars = []
    since = None
    for page in range(pages):
        params = {}
        if since:
            params["until"] = since
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe, limit=300, params=params)
        except Exception as e:
            print(f"    {symbol} 페이지 {page+1} 실패: {e}")
            break
        if not bars:
            break
        all_bars = bars + all_bars
        since = bars[0][0]

    seen = set()
    unique = []
    for b in all_bars:
        if b[0] not in seen:
            seen.add(b[0])
            unique.append(b)
    unique.sort(key=lambda x: x[0])

    df = pd.DataFrame(unique, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


class MultiSymbolBacktester:
    """멀티심볼 포트폴리오 백테스트"""

    def __init__(
        self,
        leverage: int = 3,
        initial_capital: float = 1000.0,
        fee_rate: float = 0.0006,
        max_positions: int = 3,  # 동시 최대 포지션 수
    ):
        self.leverage = leverage
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.max_positions = max_positions

    def run(self, symbol_data: dict[str, pd.DataFrame]) -> dict:
        """멀티심볼 백테스트 실행"""
        # 심볼별 지표 적용 + 전략 인스턴스
        strategies = {}
        for symbol, df in symbol_data.items():
            s = SmartTrendFuturesStrategy()
            symbol_data[symbol] = s.apply_indicators(df)
            strategies[symbol] = s

        # 공통 타임라인 생성 (모든 심볼의 타임스탬프 합집합)
        all_times = set()
        for df in symbol_data.values():
            all_times.update(df.index.tolist())
        timeline = sorted(all_times)

        capital = self.initial_capital
        positions: dict[str, dict] = {}  # symbol -> position
        trades: list[dict] = []

        for t in timeline:
            # 각 심볼 순회
            for symbol, df in symbol_data.items():
                if t not in df.index:
                    continue
                idx = df.index.get_loc(t)
                if idx < 200 or idx >= len(df) - 1:
                    continue

                curr = df.iloc[idx]
                high = curr["high"]
                low = curr["low"]
                close = curr["close"]
                strategy = strategies[symbol]

                # 열린 포지션 SL/TP 체크
                if symbol in positions:
                    pos = positions[symbol]
                    exit_price = None
                    exit_reason = None

                    if pos["side"] == "long":
                        if low <= pos["sl"]:
                            exit_price = pos["sl"]
                            exit_reason = "SL"
                        elif high >= pos["tp"]:
                            exit_price = pos["tp"]
                            exit_reason = "TP"
                    else:
                        if high >= pos["sl"]:
                            exit_price = pos["sl"]
                            exit_reason = "SL"
                        elif low <= pos["tp"]:
                            exit_price = pos["tp"]
                            exit_reason = "TP"

                    if exit_price is not None:
                        if pos["side"] == "long":
                            pnl_pct = (exit_price - pos["entry_price"]) / pos["entry_price"]
                        else:
                            pnl_pct = (pos["entry_price"] - exit_price) / pos["entry_price"]

                        leveraged_pnl_pct = pnl_pct * self.leverage
                        fee_cost = pos["margin"] * self.leverage * self.fee_rate * 2
                        gross_pnl = pos["margin"] * leveraged_pnl_pct
                        net_pnl = gross_pnl - fee_cost
                        capital += net_pnl

                        if exit_reason == "SL":
                            strategy.set_last_exit(idx)

                        trades.append({
                            "symbol": symbol.split("/")[0],
                            "entry_time": pos["entry_time"],
                            "exit_time": t,
                            "side": pos["side"],
                            "entry_price": pos["entry_price"],
                            "exit_price": exit_price,
                            "exit_reason": exit_reason,
                            "pnl_pct": pnl_pct * 100,
                            "leveraged_pnl_pct": leveraged_pnl_pct * 100,
                            "net_pnl": net_pnl,
                            "capital_after": capital,
                        })
                        del positions[symbol]

                # 신규 진입 (동시 포지션 한도 체크)
                if symbol not in positions and len(positions) < self.max_positions:
                    signal = strategy.check_signal(df, idx)
                    if signal and capital > 10:
                        entry_price = close
                        sl, tp = strategy.calculate_exit_levels(df, idx, entry_price, signal)

                        # 포지션별 자본 배분
                        alloc = capital / (self.max_positions - len(positions))
                        risk_amount = alloc * strategy.risk_per_trade
                        sl_distance = abs(entry_price - sl)
                        if sl_distance <= 0:
                            continue

                        position_size = risk_amount / sl_distance
                        margin = (position_size * entry_price) / self.leverage
                        if margin > alloc * 0.9:
                            margin = alloc * 0.9
                            position_size = (margin * self.leverage) / entry_price

                        positions[symbol] = {
                            "side": signal,
                            "entry_price": entry_price,
                            "sl": sl,
                            "tp": tp,
                            "size": position_size,
                            "margin": margin,
                            "entry_time": t,
                        }

        return self._compute_stats(trades)

    def _compute_stats(self, trades: list[dict]) -> dict:
        if not trades:
            return {"total_trades": 0, "message": "거래 없음"}

        total = len(trades)
        wins = [t for t in trades if t["net_pnl"] > 0]
        losses = [t for t in trades if t["net_pnl"] <= 0]
        win_rate = len(wins) / total * 100

        total_pnl = sum(t["net_pnl"] for t in trades)
        final_capital = trades[-1]["capital_after"]
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100

        first_trade = trades[0]["entry_time"]
        last_trade = trades[-1]["exit_time"]
        total_days = (last_trade - first_trade).total_seconds() / 86400
        total_weeks = total_days / 7 if total_days > 0 else 1
        weekly_return = total_return / total_weeks if total_weeks > 0 else 0

        equity_curve = [self.initial_capital]
        for t in trades:
            equity_curve.append(t["capital_after"])
        equity_arr = np.array(equity_curve)
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / peak * 100
        max_drawdown = drawdown.min()

        avg_win = np.mean([t["leveraged_pnl_pct"] for t in wins]) if wins else 0
        avg_loss = np.mean([t["leveraged_pnl_pct"] for t in losses]) if losses else 0

        gross_profit = sum(t["net_pnl"] for t in wins) if wins else 0
        gross_loss = abs(sum(t["net_pnl"] for t in losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        long_trades = [t for t in trades if t["side"] == "long"]
        short_trades = [t for t in trades if t["side"] == "short"]
        long_wins = len([t for t in long_trades if t["net_pnl"] > 0])
        short_wins = len([t for t in short_trades if t["net_pnl"] > 0])

        max_consecutive_loss = 0
        current_streak = 0
        for t in trades:
            if t["net_pnl"] <= 0:
                current_streak += 1
                max_consecutive_loss = max(max_consecutive_loss, current_streak)
            else:
                current_streak = 0

        # 심볼별 통계
        symbol_stats = {}
        for t in trades:
            sym = t["symbol"]
            if sym not in symbol_stats:
                symbol_stats[sym] = {"trades": 0, "wins": 0, "pnl": 0}
            symbol_stats[sym]["trades"] += 1
            if t["net_pnl"] > 0:
                symbol_stats[sym]["wins"] += 1
            symbol_stats[sym]["pnl"] += t["net_pnl"]

        return {
            "total_trades": total,
            "win_rate": win_rate,
            "total_return_pct": total_return,
            "weekly_return_pct": weekly_return,
            "total_pnl": total_pnl,
            "final_capital": final_capital,
            "max_drawdown_pct": max_drawdown,
            "avg_win_pct": avg_win,
            "avg_loss_pct": avg_loss,
            "profit_factor": profit_factor,
            "long_trades": len(long_trades),
            "long_win_rate": (long_wins / len(long_trades) * 100) if long_trades else 0,
            "short_trades": len(short_trades),
            "short_win_rate": (short_wins / len(short_trades) * 100) if short_trades else 0,
            "max_consecutive_loss": max_consecutive_loss,
            "total_days": total_days,
            "total_weeks": total_weeks,
            "symbol_stats": symbol_stats,
            "trades": trades,
        }


def print_report(stats: dict):
    print("\n" + "=" * 70)
    print("  OKX 선물 멀티심볼 백테스트 — Ultimate Ensemble Strategy")
    print("=" * 70)

    if stats.get("total_trades", 0) == 0:
        print("  거래 없음")
        return

    print(f"\n  [성과 요약]")
    print(f"  총 수익률:        {stats['total_return_pct']:+.2f}%")
    print(f"  주간 평균 수익률: {stats['weekly_return_pct']:+.2f}%")
    print(f"  최종 자본:        {stats['final_capital']:.2f} USDT (초기 1000)")
    print(f"  총 손익:          {stats['total_pnl']:+.2f} USDT")
    print(f"  Profit Factor:    {stats['profit_factor']:.2f}")
    print(f"  최대 낙폭(MDD):   {stats['max_drawdown_pct']:.2f}%")

    print(f"\n  [거래 통계]")
    print(f"  총 거래:          {stats['total_trades']}회 ({stats['total_days']:.0f}일간)")
    print(f"  승률:             {stats['win_rate']:.1f}%")
    print(f"  평균 이익(승):    {stats['avg_win_pct']:+.2f}% (레버리지 포함)")
    print(f"  평균 손실(패):    {stats['avg_loss_pct']:+.2f}% (레버리지 포함)")
    print(f"  최대 연속 손실:   {stats['max_consecutive_loss']}회")

    print(f"\n  [롱/숏 분석]")
    print(f"  롱:  {stats['long_trades']}회 (승률 {stats['long_win_rate']:.1f}%)")
    print(f"  숏:  {stats['short_trades']}회 (승률 {stats['short_win_rate']:.1f}%)")

    print(f"\n  [심볼별 성과]")
    print(f"  {'심볼':>6s} | {'거래':>4s} | {'승률':>6s} | {'PnL':>10s}")
    print("  " + "-" * 35)
    for sym, s in sorted(stats["symbol_stats"].items(), key=lambda x: x[1]["pnl"], reverse=True):
        wr = s["wins"] / s["trades"] * 100 if s["trades"] > 0 else 0
        print(f"  {sym:>6s} | {s['trades']:>4d} | {wr:>5.1f}% | {s['pnl']:>+10.2f}")

    trades = stats["trades"]
    print(f"\n  [최근 15건 거래]")
    print(f"  {'시간':>16s} | {'심볼':>5s} | {'방향':>5s} | {'진입가':>10s} | {'청산가':>10s} | {'사유':>3s} | {'PnL':>8s}")
    print("  " + "-" * 75)
    for t in trades[-15:]:
        time_str = str(t["entry_time"])[:16]
        print(
            f"  {time_str} | {t['symbol']:>5s} | {t['side']:>5s} | "
            f"{t['entry_price']:>10.4f} | {t['exit_price']:>10.4f} | "
            f"{t['exit_reason']:>3s} | {t['net_pnl']:>+8.2f}"
        )

    print("\n" + "=" * 70)
    target = 1.5
    if stats["weekly_return_pct"] >= target:
        print(f"  >> 주간 {target}% 목표 달성! ({stats['weekly_return_pct']:.2f}%)")
    else:
        print(f"  >> 주간 {target}% 목표 미달 ({stats['weekly_return_pct']:.2f}%)")
    print("=" * 70)


def main():
    exchange = create_okx_client()

    # 멀티심볼 데이터 로딩
    print("OKX 멀티심볼 데이터 로딩 중...")
    symbol_data = {}
    for symbol in SYMBOLS:
        print(f"  {symbol}...")
        try:
            df = fetch_extended_ohlcv(exchange, symbol, "1h", pages=5)
            if len(df) >= 300:
                symbol_data[symbol] = df
                days = (df.index[-1] - df.index[0]).total_seconds() / 86400
                print(f"    {len(df)}봉 ({days:.0f}일)")
            else:
                print(f"    데이터 부족: {len(df)}봉 (스킵)")
        except Exception as e:
            print(f"    실패: {e}")

    print(f"\n총 {len(symbol_data)}개 심볼 로드 완료")

    backtester = MultiSymbolBacktester(
        leverage=3,
        initial_capital=1000.0,
        fee_rate=0.0006,
        max_positions=3,
    )

    stats = backtester.run(symbol_data)
    print_report(stats)


if __name__ == "__main__":
    main()
