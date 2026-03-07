import ccxt
import pandas as pd
import time
import config

class DataFetcher:
    def __init__(self):
        # Initialize exchange instance
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True,
        })
        
    def fetch_ohlcv(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT):
        """
        Fetches OHLCV data from the exchange and returns a structured Pandas DataFrame.
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Convert columns to float (ccxt generally returns floats, but just to be safe)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

if __name__ == "__main__":
    # Test Data Fetcher
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv()
    if df is not None:
        print(f"Successfully fetched {len(df)} candles for {config.SYMBOL}.")
        print(df.tail())
