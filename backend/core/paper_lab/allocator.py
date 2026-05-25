def allocate_equal_capital(symbols: list[str], total_capital: float) -> dict[str, float]:
    """Split total_capital equally across symbols. Returns {symbol: allocation}."""
    if not symbols:
        raise ValueError("symbols must not be empty")
    if len(symbols) != len(set(symbols)):
        raise ValueError("symbols must not contain duplicates")
    if total_capital <= 0:
        raise ValueError("total_capital must be positive")
    per_symbol = total_capital / len(symbols)
    return {sym: per_symbol for sym in symbols}
