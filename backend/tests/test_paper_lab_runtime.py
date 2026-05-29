import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.paper_lab.runtime import PaperLabConfig, PaperLabRuntime
from core.paper_lab.selector import MarketCandidate


KST = ZoneInfo("Asia/Seoul")


class FakePriceProvider:
    def __init__(self, snapshots_by_tick):
        self.snapshots_by_tick = list(snapshots_by_tick)
        self.calls = 0
        self.stats = {"ticker_calls": 0, "market_load_calls": 0}

    async def get_market_snapshot(self):
        snapshot = self.snapshots_by_tick[min(self.calls, len(self.snapshots_by_tick) - 1)]
        self.calls += 1
        self.stats["ticker_calls"] = self.calls
        return snapshot


class FakePriceProviderWithOhlcv(FakePriceProvider):
    """Price provider that also serves (placeholder) OHLCV for confirmation."""

    async def get_ohlcv(self, symbol, timeframe, limit):
        return f"ohlcv:{symbol}"  # confirmer ignores content in tests


class FakeConfirmer:
    """Confirms only symbols in the allow-list (ignores OHLCV content)."""

    def __init__(self, allowed):
        self.allowed = set(allowed)

    def confirm(self, symbol, df):
        return symbol in self.allowed


class FakeRegimeProvider(FakePriceProvider):
    """Serves a real BTC/KRW close series (up/down trend) for the regime check,
    and a placeholder for candidate OHLCV."""

    def __init__(self, snapshots, btc_trend):
        super().__init__(snapshots)
        self.btc_trend = btc_trend  # "up" -> risk-on, "down" -> risk-off

    async def get_ohlcv(self, symbol, timeframe, limit):
        if symbol == "BTC/KRW":
            import pandas as pd
            if self.btc_trend == "up":
                closes = [100 + 100 * i / 249 for i in range(250)]
            else:
                closes = [200 - 100 * i / 249 for i in range(250)]
            return pd.DataFrame({"timestamp": list(range(250)), "close": closes})
        return f"ohlcv:{symbol}"


class FakeStore:
    def __init__(self):
        self.state = None
        self.snapshots = []

    def load_state(self, run_id):
        return self.state

    def save_state(self, run_id, state):
        self.state = state

    def save_snapshot(self, run_id, snapshot):
        self.snapshots.append(snapshot)


def test_first_tick_opens_equal_positions_for_all_symbols():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([[
            MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
            MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            MarketCandidate("XRP", price=500, quote_volume=8_000, percentage=1),
        ]]),
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
    )

    result = asyncio.run(runtime.tick())

    buckets = store.state["engine"]["buckets"]
    assert result["event"] == "initialized"
    assert buckets["BTC"]["position"]["qty"] == pytest.approx(2)
    assert buckets["ETH"]["position"]["qty"] == pytest.approx(20)
    assert store.state["monitored_symbol_count"] == 3
    assert store.state["symbols"] == ["BTC", "ETH"]
    assert store.state["provider_stats"]["ticker_calls"] == 1
    assert store.state["window_start"] == "2026-05-25T09:00:00+09:00"
    assert store.state["last_positions"][0]["symbol"] == "BTC"
    assert store.state["last_positions"][0]["entry_price"] == pytest.approx(50_000)
    assert store.state["last_positions"][0]["unrealized_pnl"] == pytest.approx(0)


def test_same_window_tick_only_updates_state_without_snapshot():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                MarketCandidate("BTC", price=51_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=2),
                MarketCandidate("XRP", price=500, quote_volume=20_000, percentage=10),
            ],
        ]),
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "updated"
    assert store.snapshots == []
    assert store.state["last_prices"] == {"BTC": 51_000, "ETH": 5_100}
    assert store.state["candidate_symbols"][0] == "XRP"
    assert store.state["monitored_symbol_count"] == 3


def test_same_window_rebalances_when_new_candidates_are_much_better_after_hold_time():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 11, 1, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(
            selection_limit=2,
            total_capital=200_000,
            min_quote_volume=0,
            intraday_rebalance_min_minutes=60,
            intraday_score_improvement=0.10,
        ),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
                MarketCandidate("XRP", price=500, quote_volume=8_000, percentage=1),
            ],
            [
                MarketCandidate("BTC", price=51_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=1),
                MarketCandidate("XRP", price=1_000, quote_volume=50_000, percentage=15),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "intraday_rebalanced"
    assert store.state["symbols"] == ["XRP", "BTC"]
    assert store.state["rebalance_reason"] == "intraday_candidate_rotation"
    assert store.state["rebalance_history"][-1]["event"] == "intraday_rebalanced"


def test_same_window_does_not_rebalance_before_min_hold_time():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 10, 30, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(
            selection_limit=2,
            total_capital=200_000,
            min_quote_volume=0,
            intraday_rebalance_min_minutes=60,
            intraday_score_improvement=0.10,
        ),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                MarketCandidate("XRP", price=1_000, quote_volume=50_000, percentage=15),
                MarketCandidate("BTC", price=51_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=1),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "updated"
    assert store.state["symbols"] == ["BTC", "ETH"]


def test_default_intraday_rebalance_is_conservative_after_one_hour():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 11, 1, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                MarketCandidate("XRP", price=1_000, quote_volume=50_000, percentage=15),
                MarketCandidate("BTC", price=51_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=1),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "updated"
    assert store.state["symbols"] == ["BTC", "ETH"]


def test_default_intraday_rebalance_requires_large_score_improvement_after_hold_time():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 13, 1, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=100_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=90_000, percentage=2),
            ],
            [
                MarketCandidate("XRP", price=1_000, quote_volume=100_000, percentage=4),
                MarketCandidate("BTC", price=51_000, quote_volume=100_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=90_000, percentage=2),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "updated"
    assert store.state["symbols"] == ["BTC", "ETH"]


def test_confirmation_buys_only_confirmed_and_holds_cash_for_rest():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(
            selection_limit=3, total_capital=300_000,
            min_quote_volume=0, shortlist_limit=5,
        ),
        FakePriceProviderWithOhlcv([[
            MarketCandidate("AAA", price=100, quote_volume=10_000, percentage=5),
            MarketCandidate("BBB", price=100, quote_volume=9_000, percentage=4),
            MarketCandidate("CCC", price=100, quote_volume=8_000, percentage=3),
        ]]),
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        confirmer=FakeConfirmer(["AAA"]),  # only AAA passes the entry gate
    )

    result = asyncio.run(runtime.tick())

    buckets = store.state["engine"]["buckets"]
    assert result["event"] == "initialized"
    # 1 of 3 slots filled -> per_slot 100,000 -> AAA qty 1000; rest stays cash
    assert buckets["AAA"]["position"]["qty"] == pytest.approx(1000)
    assert "BBB" not in buckets and "CCC" not in buckets
    assert store.state["symbols"] == ["AAA"]
    assert store.state["last_summary"]["total_equity"] == pytest.approx(300_000)
    assert store.state["last_summary"]["open_position_count"] == 1
    # reserved cash bucket is hidden from reported positions
    assert all(p["symbol"] != "__CASH__" for p in store.state["last_positions"])
    assert [p["symbol"] for p in store.state["last_positions"]] == ["AAA"]


def test_regime_off_blocks_new_entries():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=3, total_capital=300_000, min_quote_volume=0,
                       shortlist_limit=5),
        FakeRegimeProvider([[
            MarketCandidate("AAA", price=100, quote_volume=10_000, percentage=5),
            MarketCandidate("BBB", price=100, quote_volume=9_000, percentage=4),
        ]], btc_trend="down"),  # BTC below EMA -> risk-off
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        confirmer=FakeConfirmer(["AAA", "BBB"]),  # would confirm, but regime blocks
    )

    result = asyncio.run(runtime.tick())

    assert result["event"] == "initialized"
    assert store.state["symbols"] == []  # risk-off -> all cash
    assert store.state["last_summary"]["open_position_count"] == 0
    assert store.state["last_summary"]["total_equity"] == pytest.approx(300_000)


def test_regime_on_allows_entries():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=3, total_capital=300_000, min_quote_volume=0,
                       shortlist_limit=5),
        FakeRegimeProvider([[
            MarketCandidate("AAA", price=100, quote_volume=10_000, percentage=5),
            MarketCandidate("BBB", price=100, quote_volume=9_000, percentage=4),
        ]], btc_trend="up"),  # BTC above EMA -> risk-on
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        confirmer=FakeConfirmer(["AAA"]),
    )

    result = asyncio.run(runtime.tick())

    assert result["event"] == "initialized"
    assert store.state["symbols"] == ["AAA"]
    assert "AAA" in store.state["engine"]["buckets"]


def test_no_confirmed_candidates_holds_all_cash():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=3, total_capital=300_000, min_quote_volume=0),
        FakePriceProviderWithOhlcv([[
            MarketCandidate("AAA", price=100, quote_volume=10_000, percentage=5),
            MarketCandidate("BBB", price=100, quote_volume=9_000, percentage=4),
        ]]),
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        confirmer=FakeConfirmer([]),  # nothing confirmed -> fully in cash
    )

    result = asyncio.run(runtime.tick())

    assert result["event"] == "initialized"
    assert store.state["symbols"] == []
    assert store.state["last_summary"]["total_equity"] == pytest.approx(300_000)
    assert store.state["last_summary"]["open_position_count"] == 0
    assert store.state["last_positions"] == []


def test_stop_loss_liquidates_losing_symbol_and_records_realized():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 10, 30, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                # BTC drops -6% (breaches -5% stop), ETH up. Same candidate set => no rebalance.
                MarketCandidate("BTC", price=47_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=2),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    buckets = store.state["engine"]["buckets"]
    assert result["event"] == "stop_loss"
    assert buckets["BTC"]["position"] is None  # liquidated
    assert buckets["ETH"]["position"] is not None  # still held
    assert store.state["last_summary"]["realized_pnl"] == pytest.approx((47_000 - 50_000) * 2)


def test_daily_loss_limit_liquidates_all_and_halts_reentry():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 10, 30, tzinfo=KST),
        datetime(2026, 5, 25, 11, 0, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                # Equity 200,000 -> 184,000 = -8% > 5% daily limit -> liquidate all + halt.
                MarketCandidate("BTC", price=44_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=4_800, quote_volume=9_000, percentage=2),
            ],
            [
                # Even with much better candidates, halted window must not re-enter.
                # (Held symbols BTC/ETH must remain priceable in the snapshot.)
                MarketCandidate("XRP", price=1_000, quote_volume=99_000, percentage=30),
                MarketCandidate("BTC", price=44_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=4_800, quote_volume=9_000, percentage=2),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    halt = asyncio.run(runtime.tick())
    after = asyncio.run(runtime.tick())

    assert halt["event"] == "daily_loss_halt"
    assert store.state["halted"] is True
    buckets = store.state["engine"]["buckets"]
    assert all(b["position"] is None for b in buckets.values())
    assert store.state["last_summary"]["realized_pnl"] == pytest.approx(
        (44_000 - 50_000) * 2 + (4_800 - 5_000) * 20
    )
    assert after["event"] == "halted"
    assert "XRP" not in store.state["engine"]["buckets"]  # no re-entry into new names


def test_realized_pnl_from_stop_loss_is_reported_in_daily_snapshot():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 25, 10, 30, tzinfo=KST),
        datetime(2026, 5, 26, 9, 1, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                MarketCandidate("BTC", price=47_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=2),
            ],
            [
                MarketCandidate("BTC", price=47_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_100, quote_volume=9_000, percentage=2),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())   # open
    asyncio.run(runtime.tick())   # stop-loss BTC (realized -6000), same window
    asyncio.run(runtime.tick())   # next window -> snapshot

    assert len(store.snapshots) == 1
    assert store.snapshots[0]["summary"]["realized_pnl"] == pytest.approx((47_000 - 50_000) * 2)


def test_new_kst_9am_window_snapshots_and_rebalances():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 26, 9, 1, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(selection_limit=2, total_capital=200_000, min_quote_volume=0),
        FakePriceProvider([
            [
                MarketCandidate("BTC", price=50_000, quote_volume=10_000, percentage=3),
                MarketCandidate("ETH", price=5_000, quote_volume=9_000, percentage=2),
            ],
            [
                MarketCandidate("BTC", price=60_000, quote_volume=9_000, percentage=1),
                MarketCandidate("ETH", price=4_000, quote_volume=8_000, percentage=1),
                MarketCandidate("XRP", price=1_000, quote_volume=50_000, percentage=10),
            ],
        ]),
        store,
        now_fn=lambda: next(now_values),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "daily_rebalanced"
    assert len(store.snapshots) == 1
    assert store.snapshots[0]["window_start"] == "2026-05-25T09:00:00+09:00"
    assert store.snapshots[0]["summary"]["total_equity"] == pytest.approx(200_000)
    assert store.snapshots[0]["positions"][0]["symbol"] == "BTC"
    assert store.snapshots[0]["positions"][0]["mark_price"] == pytest.approx(60_000)
    assert store.snapshots[0]["positions"][0]["unrealized_pnl"] == pytest.approx(20_000)
    buckets = store.state["engine"]["buckets"]
    assert store.state["symbols"] == ["XRP", "BTC"]
    assert buckets["XRP"]["position"]["qty"] == pytest.approx(200_000 / 2 / 1_000)
    assert buckets["BTC"]["position"]["qty"] == pytest.approx(200_000 / 2 / 60_000)
    assert store.state["window_start"] == "2026-05-26T09:00:00+09:00"
