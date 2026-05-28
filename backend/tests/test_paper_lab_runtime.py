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
