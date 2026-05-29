from core.paper_lab.selector import MarketCandidate, select_top_markets


def test_select_top_markets_filters_low_liquidity_and_scores_candidates():
    candidates = [
        MarketCandidate("BTC/KRW", price=100, quote_volume=20_000_000_000, percentage=1.0),
        MarketCandidate("ETH/KRW", price=100, quote_volume=15_000_000_000, percentage=3.0),
        MarketCandidate("LOW/KRW", price=100, quote_volume=1_000_000, percentage=100.0),
        MarketCandidate("XRP/KRW", price=100, quote_volume=8_000_000_000, percentage=-1.0),
    ]

    selected = select_top_markets(candidates, limit=2, min_quote_volume=5_000_000_000)

    assert [item.symbol for item in selected] == ["ETH/KRW", "BTC/KRW"]
    assert all(item.symbol != "LOW/KRW" for item in selected)
    assert selected[0].score > selected[1].score


def test_select_top_markets_excludes_overheated_candidates():
    candidates = [
        MarketCandidate("HOT/KRW", price=100, quote_volume=10_000_000_000, percentage=40.0),
        MarketCandidate("OK/KRW", price=100, quote_volume=10_000_000_000, percentage=10.0),
    ]

    selected = select_top_markets(
        candidates, limit=10, min_quote_volume=0, max_percentage=25.0
    )

    symbols = [item.symbol for item in selected]
    assert "HOT/KRW" not in symbols  # already pumped +40% -> skipped
    assert "OK/KRW" in symbols


def test_select_top_markets_uses_stable_symbol_order_for_ties():
    candidates = [
        MarketCandidate("CCC/KRW", price=100, quote_volume=10_000, percentage=1.0),
        MarketCandidate("AAA/KRW", price=100, quote_volume=10_000, percentage=1.0),
        MarketCandidate("BBB/KRW", price=100, quote_volume=10_000, percentage=1.0),
    ]

    selected = select_top_markets(candidates, limit=3, min_quote_volume=0)

    assert [item.symbol for item in selected] == ["AAA/KRW", "BBB/KRW", "CCC/KRW"]
