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


class DelistingExchange:
    """First ticker batch contains a stale code and Upbit 404s the whole batch;
    after a forced market reload the stale code is gone and the retry succeeds."""

    def __init__(self):
        self.load_markets_calls = 0
        self.fetch_tickers_calls = 0
        self._delisted = True

    def load_markets(self, reload=False):
        self.load_markets_calls += 1
        if reload:
            self._delisted = False
        markets = {"BTC/KRW": {"active": True}, "ETH/KRW": {"active": True}}
        if self._delisted:
            markets["GHOST/KRW"] = {"active": True}
        return markets

    def fetch_tickers(self, symbols):
        self.fetch_tickers_calls += 1
        if any(s == "GHOST/KRW" for s in symbols):
            raise Exception('upbit {"error":{"name":404,"message":"Code not found"}}')
        return {
            symbol: {"last": 100, "quoteVolume": 1_000_000_000, "percentage": 1.5}
            for symbol in symbols
        }


def test_price_provider_self_heals_on_delisted_market_code():
    provider = UpbitTickerPriceProvider()
    fake_exchange = DelistingExchange()
    provider.fetcher.exchange = fake_exchange

    result = asyncio.run(provider.get_market_snapshot())

    # Reloaded the universe and retried the ticker batch (no exception bubbles up).
    assert fake_exchange.load_markets_calls == 2
    assert fake_exchange.fetch_tickers_calls == 2
    assert [candidate.symbol for candidate in result] == ["BTC/KRW", "ETH/KRW"]
    assert provider.stats["last_error"] is None


class SuspendedMarketExchange:
    """A code stays in /market/all even after a reload (trading suspension), and
    Upbit 404s any ticker batch containing it. The resilient fetch must bisect,
    drop the suspended code, and still return the other tickers."""

    def __init__(self):
        self.load_markets_calls = 0
        self.fetch_tickers_calls = 0

    def load_markets(self, reload=False):
        self.load_markets_calls += 1
        return {
            "BTC/KRW": {"active": True},
            "ETH/KRW": {"active": True},
            "SUSP/KRW": {"active": True},  # listed but suspended → reload keeps it
        }

    def fetch_tickers(self, symbols):
        self.fetch_tickers_calls += 1
        if "SUSP/KRW" in symbols:
            raise Exception('upbit {"error":{"name":404,"message":"Code not found"}}')
        return {
            symbol: {"last": 100, "quoteVolume": 1_000_000_000, "percentage": 1.5}
            for symbol in symbols
        }


def test_price_provider_skips_suspended_code_via_bisection():
    provider = UpbitTickerPriceProvider()
    fake_exchange = SuspendedMarketExchange()
    provider.fetcher.exchange = fake_exchange

    result = asyncio.run(provider.get_market_snapshot())

    # The suspended code is dropped; the remaining markets still come through and
    # no exception bubbles up to crash the tick.
    assert [candidate.symbol for candidate in result] == ["BTC/KRW", "ETH/KRW"]
    assert provider.stats["last_error"] is None


def test_price_provider_batches_ticker_requests_for_large_krw_market_set():
    class BatchLimitedExchange:
        def __init__(self):
            self.fetch_tickers_batches = []

        def load_markets(self):
            return {f"COIN{i:03d}/KRW": {"active": True} for i in range(205)}

        def fetch_tickers(self, symbols):
            self.fetch_tickers_batches.append(list(symbols))
            if len(symbols) > 100:
                raise ValueError("too many symbols in one ticker request")
            return {
                symbol: {
                    "last": 100,
                    "quoteVolume": 1_000_000_000,
                    "percentage": 1.5,
                }
                for symbol in symbols
            }

    provider = UpbitTickerPriceProvider()
    fake_exchange = BatchLimitedExchange()
    provider.fetcher.exchange = fake_exchange

    snapshot = asyncio.run(provider.get_market_snapshot())

    assert len(snapshot) == 205
    assert [len(batch) for batch in fake_exchange.fetch_tickers_batches] == [100, 100, 5]
