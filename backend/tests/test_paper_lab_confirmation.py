import pandas as pd

from core.paper_lab.confirmation import EnsembleConfirmer, StrategyConfirmer


def _tiny_df(n):
    return pd.DataFrame({
        "timestamp": range(n),
        "open": [100.0] * n, "high": [101.0] * n,
        "low": [99.0] * n, "close": [100.0] * n, "volume": [1.0] * n,
    })


def test_ensemble_confirmer_loads_configured_strategies():
    c = EnsembleConfirmer(["momentum_aggressive_4h", "trend_rider_4h_v1"])
    assert c.strategy_names == ["momentum_aggressive_4h", "trend_rider_4h_v1"]
    assert len(c._strategies) == 2


def test_ensemble_confirmer_rejects_insufficient_history():
    c = EnsembleConfirmer(["momentum_aggressive_4h", "trend_rider_4h_v1"])
    assert c.confirm("X/KRW", None) is False          # no data
    assert c.confirm("X/KRW", _tiny_df(50)) is False  # < min_rows (new listing)


def test_ensemble_confirmer_flat_market_no_signal():
    # 250 flat candles -> no momentum/trend buy signal from either strategy.
    c = EnsembleConfirmer(["momentum_aggressive_4h", "trend_rider_4h_v1"])
    assert c.confirm("X/KRW", _tiny_df(250)) is False


def test_strategy_confirmer_still_rejects_short_history():
    c = StrategyConfirmer("surge_catcher_15m")
    assert c.confirm("X/KRW", None) is False
    assert c.confirm("X/KRW", _tiny_df(10)) is False
