import ccxt
import pandas as pd
import time
from core import config
from sqlalchemy.orm import Session
import models

class DataFetcher:
    def __init__(self):
        # Initialize exchange instance
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange = exchange_class({
            'apiKey': config.API_KEY,
            'secret': config.API_SECRET,
            'enableRateLimit': True,
        })
        
    def fetch_ohlcv(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=config.LIMIT, start_date=None, end_date=None, db: Session = None):
        """
        Fetches OHLCV data with Database Caching.
        Steps:
        1. Try to load requested range from DB.
        2. Identify gaps or fetch missing data from API.
        3. Save new data to DB.
        """
        try:
            since = None
            until = None
            
            if start_date:
                since = self.exchange.parse8601(f"{start_date}T00:00:00Z")
            if end_date:
                until = self.exchange.parse8601(f"{end_date}T23:59:59Z")
            
            # If no start_date, determine roughly based on limit
            if not since and limit:
                # Estimate since based on limit and current time
                duration = self.exchange.parse_timeframe(timeframe) * 1000
                since = self.exchange.milliseconds() - (duration * (limit + 10)) # safety margin

            # 1. Check DB Cache
            db_data = []
            if db:
                query = db.query(models.OHLCV).filter(
                    models.OHLCV.symbol == symbol,
                    models.OHLCV.timeframe == timeframe,
                    models.OHLCV.timestamp >= since
                )
                if until:
                    query = query.filter(models.OHLCV.timestamp <= until)
                
                db_records = query.order_by(models.OHLCV.timestamp.asc()).all()
                db_data = [[r.timestamp, r.open, r.high, r.low, r.close, r.volume] for r in db_records]

            # 2. Decide if we need to fetch more
            ohlcv = db_data
            
            # Simplified Logic: If no DB data or data is insufficient, fetch everything from API for that range
            # In a production app, we would fetch only the GAPS.
            if len(ohlcv) < (limit if limit else 10):
                print(f"Cache miss for {symbol} {timeframe}. Fetching from exchange...")
                # Use existing robust fetch logic
                ohlcv_api = self._fetch_from_api_robust(symbol, timeframe, limit, since, until)
                
                if ohlcv_api and db:
                    # Save newly fetched data to DB
                    self._save_to_db(db, symbol, timeframe, ohlcv_api)
                
                ohlcv = ohlcv_api
            else:
                print(f"Loading {len(ohlcv)} candles from DB cache for {symbol} {timeframe}.")

            if not ohlcv: return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Final trim for limit
            if limit and not start_date:
                df = df.tail(limit)
                
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def _fetch_from_api_robust(self, symbol, timeframe, limit, since, until):
        ohlcv = []
        try:
            # Re-use logic for date-range vs limit
            if since and not limit:
                current_since = since
                target_until = until if until else self.exchange.milliseconds()
                while current_since < target_until:
                    try:
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=200)
                        if not batch: break
                        last_timestamp = batch[-1][0]
                        current_since = last_timestamp + 1
                        ohlcv.extend(batch)
                        if last_timestamp >= target_until: break
                        time.sleep(max(0.2, self.exchange.rateLimit / 1000))
                    except Exception as e:
                        if "too_many_requests" in str(e).lower(): time.sleep(5); continue
                        break
            else:
                # Limit based backward fetch
                limit = limit or config.LIMIT
                chunk_size = 200 if config.EXCHANGE_ID == 'upbit' else 500
                last_since = None
                while len(ohlcv) < limit:
                    fetch_limit = min(chunk_size, limit - len(ohlcv))
                    if last_since is None:
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, limit=fetch_limit)
                    else:
                        duration = self.exchange.parse_timeframe(timeframe) * 1000
                        batch = self.exchange.fetch_ohlcv(symbol, timeframe, since=last_since - (duration * fetch_limit), limit=fetch_limit)
                    if not batch: break
                    ohlcv = batch + ohlcv
                    last_since = batch[0][0]
                    time.sleep(max(0.2, self.exchange.rateLimit / 1000))
            return ohlcv
        except Exception as e:
            print(f"API fetch error: {e}")
            return []

    def _save_to_db(self, db: Session, symbol: str, timeframe: str, data: list):
        """
        Saves candles to DB, avoiding duplicates.
        """
        try:
            new_records = []
            for candle in data:
                # Check if exists
                exists = db.query(models.OHLCV.id).filter(
                    models.OHLCV.symbol == symbol,
                    models.OHLCV.timeframe == timeframe,
                    models.OHLCV.timestamp == candle[0]
                ).first()
                
                if not exists:
                    new_records.append(models.OHLCV(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=candle[0],
                        open=candle[1],
                        high=candle[2],
                        low=candle[3],
                        close=candle[4],
                        volume=candle[5]
                    ))
            
            if new_records:
                db.bulk_save_objects(new_records)
                db.commit()
                print(f"Saved {len(new_records)} new candles to DB cache.")
        except Exception as e:
            db.rollback()
            print(f"Failed to save OHLCV to DB: {e}")

if __name__ == "__main__":
    # Test Data Fetcher
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv()
    if df is not None:
        print(f"Successfully fetched {len(df)} candles for {config.SYMBOL}.")
        print(df.tail())
