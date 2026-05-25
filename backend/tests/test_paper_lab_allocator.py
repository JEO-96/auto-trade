import pytest
from core.paper_lab.allocator import allocate_equal_capital


def test_four_symbols_equal_allocation():
    result = allocate_equal_capital(["BTC", "ETH", "XRP", "SOL"], 1_000_000)
    assert result == {"BTC": 250_000, "ETH": 250_000, "XRP": 250_000, "SOL": 250_000}


def test_two_symbols_equal_allocation():
    result = allocate_equal_capital(["BTC", "ETH"], 100)
    assert result["BTC"] == pytest.approx(50.0)
    assert result["ETH"] == pytest.approx(50.0)


def test_single_symbol_gets_full_capital():
    result = allocate_equal_capital(["BTC"], 500_000)
    assert result == {"BTC": 500_000}


def test_duplicate_symbols_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        allocate_equal_capital(["BTC", "BTC"], 1_000_000)


def test_empty_symbols_rejected():
    with pytest.raises(ValueError, match="empty"):
        allocate_equal_capital([], 1_000_000)


def test_zero_capital_rejected():
    with pytest.raises(ValueError):
        allocate_equal_capital(["BTC"], 0)


def test_negative_capital_rejected():
    with pytest.raises(ValueError):
        allocate_equal_capital(["BTC"], -100)


def test_returns_all_requested_symbols():
    symbols = ["BTC", "ETH", "XRP"]
    result = allocate_equal_capital(symbols, 300_000)
    assert set(result.keys()) == set(symbols)


def test_allocations_sum_to_total():
    result = allocate_equal_capital(["BTC", "ETH", "XRP"], 100_000)
    assert sum(result.values()) == pytest.approx(100_000)
