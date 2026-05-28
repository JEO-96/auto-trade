import pytest
from core.paper_lab.engine import PaperLabEngine, SymbolBucket, PaperPosition, PaperTrade


# --- Isolated budget buckets ---

def test_four_symbols_get_equal_budgets():
    engine = PaperLabEngine(["BTC", "ETH", "XRP", "SOL"], 1_000_000)
    for sym in ["BTC", "ETH", "XRP", "SOL"]:
        assert engine.state.buckets[sym].cash == pytest.approx(250_000)


def test_buying_one_symbol_does_not_affect_others():
    engine = PaperLabEngine(["BTC", "ETH"], 1_000_000)
    engine.buy("BTC", price=50_000)
    assert engine.state.buckets["BTC"].cash == pytest.approx(0, abs=1e-6)
    assert engine.state.buckets["ETH"].cash == pytest.approx(500_000)


# --- All symbols can open positions ---

def test_all_selected_symbols_can_open_positions():
    engine = PaperLabEngine(["BTC", "ETH", "XRP", "SOL"], 1_000_000)
    engine.buy("BTC", price=50_000_000)
    engine.buy("ETH", price=3_000_000)
    engine.buy("XRP", price=1_000)
    engine.buy("SOL", price=200_000)
    for sym in ["BTC", "ETH", "XRP", "SOL"]:
        assert engine.state.buckets[sym].position is not None


def test_each_symbol_position_uses_only_its_allocation():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    engine.buy("BTC", price=50_000)   # 2 BTC from 100k
    engine.buy("ETH", price=5_000)    # 20 ETH from 100k
    assert engine.state.buckets["BTC"].position.qty == pytest.approx(2.0)
    assert engine.state.buckets["ETH"].position.qty == pytest.approx(20.0)


# --- Sell records realized PnL, returns cash ---

def test_sell_returns_cash_to_same_symbol_bucket():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)   # 2 BTC at 50k
    engine.sell("BTC", price=60_000)
    assert engine.state.buckets["BTC"].cash == pytest.approx(120_000)


def test_sell_returns_pnl_trade_object():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    trade = engine.sell("BTC", price=60_000)
    assert isinstance(trade, PaperTrade)
    assert trade.realized_pnl == pytest.approx(20_000)


def test_sell_clears_position():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    engine.sell("BTC", price=60_000)
    assert engine.state.buckets["BTC"].position is None


def test_realized_pnl_recorded_in_bucket():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    engine.sell("BTC", price=55_000)
    assert engine.state.buckets["BTC"].realized_pnl == pytest.approx(10_000)


def test_realized_pnl_isolated_per_symbol():
    engine = PaperLabEngine(["BTC", "ETH"], 1_000_000)
    engine.buy("BTC", price=50_000)
    engine.sell("BTC", price=60_000)   # +100k PnL on BTC
    assert engine.state.buckets["ETH"].realized_pnl == pytest.approx(0)
    assert engine.state.buckets["BTC"].realized_pnl == pytest.approx(100_000)


def test_loss_trade_reduces_bucket_cash():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)   # 2 BTC
    engine.sell("BTC", price=40_000)  # 2 BTC at loss
    assert engine.state.buckets["BTC"].cash == pytest.approx(80_000)
    assert engine.state.buckets["BTC"].realized_pnl == pytest.approx(-20_000)


# --- Daily summary ---

def test_summary_total_equity_no_positions():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    summary = engine.summary({"BTC": 50_000, "ETH": 3_000})
    assert summary["total_equity"] == pytest.approx(200_000)


def test_summary_fields_present():
    engine = PaperLabEngine(["BTC"], 100_000)
    summary = engine.summary({"BTC": 50_000})
    assert "total_equity" in summary
    assert "realized_pnl" in summary
    assert "unrealized_pnl" in summary
    assert "open_position_count" in summary


def test_summary_with_open_position_unrealized_pnl():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)   # 2 BTC at 50k
    summary = engine.summary({"BTC": 55_000})
    assert summary["unrealized_pnl"] == pytest.approx(10_000)
    assert summary["total_equity"] == pytest.approx(110_000)
    assert summary["open_position_count"] == 1


def test_summary_after_sell_no_unrealized():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    engine.sell("BTC", price=60_000)
    summary = engine.summary({"BTC": 60_000})
    assert summary["realized_pnl"] == pytest.approx(20_000)
    assert summary["unrealized_pnl"] == pytest.approx(0)
    assert summary["open_position_count"] == 0


def test_summary_multiple_symbols_mixed():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    engine.buy("BTC", price=50_000)   # 2 BTC from 100k
    engine.buy("ETH", price=5_000)    # 20 ETH from 100k
    # BTC mark 55k -> unrealized +10k; ETH mark 4500 -> unrealized -10k
    summary = engine.summary({"BTC": 55_000, "ETH": 4_500})
    assert summary["open_position_count"] == 2
    assert summary["unrealized_pnl"] == pytest.approx(0, abs=1e-6)


def test_position_details_include_symbol_level_unrealized_pnl():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    engine.buy("BTC", price=50_000)
    engine.buy("ETH", price=5_000)

    details = engine.position_details({"BTC": 55_000, "ETH": 4_500})

    by_symbol = {detail["symbol"]: detail for detail in details}
    assert by_symbol["BTC"]["entry_price"] == pytest.approx(50_000)
    assert by_symbol["BTC"]["mark_price"] == pytest.approx(55_000)
    assert by_symbol["BTC"]["unrealized_pnl"] == pytest.approx(10_000)
    assert by_symbol["BTC"]["return_pct"] == pytest.approx(10)
    assert by_symbol["ETH"]["unrealized_pnl"] == pytest.approx(-10_000)
    assert by_symbol["ETH"]["return_pct"] == pytest.approx(-10)


def test_position_details_include_closed_bucket_cash_and_realized_pnl():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    engine.sell("BTC", price=40_000)

    details = engine.position_details({})

    assert details == [
        {
            "symbol": "BTC",
            "cash": pytest.approx(80_000),
            "position_open": False,
            "realized_pnl": pytest.approx(-20_000),
        }
    ]


# --- Error cases ---

def test_buy_rejects_zero_price():
    engine = PaperLabEngine(["BTC"], 100_000)
    with pytest.raises(ValueError, match="price"):
        engine.buy("BTC", price=0)


def test_buy_rejects_negative_qty():
    engine = PaperLabEngine(["BTC"], 100_000)
    with pytest.raises(ValueError, match="qty"):
        engine.buy("BTC", price=50_000, qty=-1)


def test_sell_rejects_zero_price():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    with pytest.raises(ValueError, match="price"):
        engine.sell("BTC", price=0)


def test_summary_requires_mark_price_for_open_position():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    engine.buy("BTC", price=50_000)
    with pytest.raises(KeyError, match="BTC"):
        engine.summary({"ETH": 5_000})


def test_summary_allows_missing_mark_price_without_open_position():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    summary = engine.summary({"ETH": 5_000})
    assert summary["total_equity"] == pytest.approx(200_000)


def test_buy_unknown_symbol_raises_key_error():
    engine = PaperLabEngine(["BTC"], 100_000)
    with pytest.raises(KeyError):
        engine.buy("ETH", price=5_000)


def test_double_buy_same_symbol_raises():
    engine = PaperLabEngine(["BTC"], 100_000)
    engine.buy("BTC", price=50_000)
    with pytest.raises(ValueError):
        engine.buy("BTC", price=55_000)


def test_sell_without_position_raises():
    engine = PaperLabEngine(["BTC"], 100_000)
    with pytest.raises(ValueError):
        engine.sell("BTC", price=50_000)


def test_engine_round_trips_to_dict():
    engine = PaperLabEngine(["BTC", "ETH"], 200_000)
    engine.buy("BTC", price=50_000)
    engine.sell("BTC", price=60_000)
    engine.buy("ETH", price=5_000)

    restored = PaperLabEngine.from_dict(engine.to_dict())

    assert restored.state.buckets["BTC"].cash == pytest.approx(120_000)
    assert restored.state.buckets["BTC"].realized_pnl == pytest.approx(20_000)
    assert restored.state.buckets["ETH"].position.qty == pytest.approx(20)
