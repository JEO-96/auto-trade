import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.paper_lab.runtime import PaperLabConfig, PaperLabRuntime


KST = ZoneInfo("Asia/Seoul")


class FakePriceProvider:
    def __init__(self, prices_by_tick):
        self.prices_by_tick = list(prices_by_tick)
        self.calls = 0

    async def get_prices(self, symbols):
        prices = self.prices_by_tick[min(self.calls, len(self.prices_by_tick) - 1)]
        self.calls += 1
        return {symbol: prices[symbol] for symbol in symbols}


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
        PaperLabConfig(symbols=["BTC", "ETH"], total_capital=200_000),
        FakePriceProvider([{"BTC": 50_000, "ETH": 5_000}]),
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
    )

    result = asyncio.run(runtime.tick())

    buckets = store.state["engine"]["buckets"]
    assert result["event"] == "initialized"
    assert buckets["BTC"]["position"]["qty"] == pytest.approx(2)
    assert buckets["ETH"]["position"]["qty"] == pytest.approx(20)
    assert store.state["window_start"] == "2026-05-25T09:00:00+09:00"


def test_same_window_tick_only_updates_state_without_snapshot():
    store = FakeStore()
    runtime = PaperLabRuntime(
        PaperLabConfig(symbols=["BTC", "ETH"], total_capital=200_000),
        FakePriceProvider([
            {"BTC": 50_000, "ETH": 5_000},
            {"BTC": 51_000, "ETH": 5_100},
        ]),
        store,
        now_fn=lambda: datetime(2026, 5, 25, 10, 0, tzinfo=KST),
    )

    asyncio.run(runtime.tick())
    result = asyncio.run(runtime.tick())

    assert result["event"] == "updated"
    assert store.snapshots == []
    assert store.state["last_prices"] == {"BTC": 51_000, "ETH": 5_100}


def test_new_kst_9am_window_snapshots_and_rebalances():
    store = FakeStore()
    now_values = iter([
        datetime(2026, 5, 25, 10, 0, tzinfo=KST),
        datetime(2026, 5, 26, 9, 1, tzinfo=KST),
    ])
    runtime = PaperLabRuntime(
        PaperLabConfig(symbols=["BTC", "ETH"], total_capital=200_000),
        FakePriceProvider([
            {"BTC": 50_000, "ETH": 5_000},
            {"BTC": 60_000, "ETH": 4_000},
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
    buckets = store.state["engine"]["buckets"]
    assert buckets["BTC"]["position"]["qty"] == pytest.approx(200_000 / 2 / 60_000)
    assert buckets["ETH"]["position"]["qty"] == pytest.approx(200_000 / 2 / 4_000)
    assert store.state["window_start"] == "2026-05-26T09:00:00+09:00"
