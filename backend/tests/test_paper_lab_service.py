import asyncio

from core.paper_lab.service import UpbitTickerPriceProvider


class FakeExchange:
    def __init__(self):
        self.load_markets_calls = 0
        self.fetch_tickers_calls = 0

    def load_markets(self):
        self.load_markets_calls += 1
        return {
            "BTC/KRW": {"active": True},
            "ETH/KRW": {"active": True},
            "BTC/USDT": {"active": True},
            "OLD/KRW": {"active": False},
        }

    def fetch_tickers(self, symbols):
        self.fetch_tickers_calls += 1
        return {
            symbol: {
                "last": 100,
                "quoteVolume": 1_000_000_000,
                "percentage": 1.5,
            }
            for symbol in symbols
        }


def test_price_provider_caches_krw_market_symbols_between_ticks():
    provider = UpbitTickerPriceProvider()
    fake_exchange = FakeExchange()
    provider.fetcher.exchange = fake_exchange

    first = asyncio.run(provider.get_market_snapshot())
    second = asyncio.run(provider.get_market_snapshot())

    assert fake_exchange.load_markets_calls == 1
    assert fake_exchange.fetch_tickers_calls == 2
    assert [candidate.symbol for candidate in first] == ["BTC/KRW", "ETH/KRW"]
    assert [candidate.symbol for candidate in second] == ["BTC/KRW", "ETH/KRW"]
    assert provider.stats["market_load_calls"] == 1
    assert provider.stats["ticker_calls"] == 2
