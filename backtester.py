import pandas as pd
from data_fetcher import DataFetcher
from strategy import MomentumBreakoutStrategy
import config

class Backtester:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.strategy = MomentumBreakoutStrategy()
        
    def run(self, symbol=config.SYMBOL, timeframe=config.TIMEFRAME, limit=1000):
        print(f"Running backtest on {symbol} {timeframe} for the last {limit} candles...")
        df = self.fetcher.fetch_ohlcv(symbol, timeframe, limit)
        if df is None or len(df) == 0:
            print("No data fetched.")
            return
            
        df = self.strategy.apply_indicators(df)
        
        capital = 10000.0  # Starting capital USD
        position = 0.0     # Asset amount
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        is_in_position = False
        
        trades = []
        
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            timestamp = current_row['timestamp']
            close = current_row['close']
            
            # Check for Exit Condition if in position
            if is_in_position:
                if current_row['low'] <= stop_loss:
                    print(f"[{timestamp}] Stop Loss hit at {stop_loss:.2f}. Sold out.")
                    capital = position * stop_loss
                    position = 0.0
                    is_in_position = False
                    trades.append({'type': 'SELL_SL', 'price': stop_loss, 'capital': capital, 'time': timestamp})
                elif current_row['high'] >= take_profit:
                    print(f"[{timestamp}] Take Profit hit at {take_profit:.2f}. Sold out.")
                    capital = position * take_profit
                    position = 0.0
                    is_in_position = False
                    trades.append({'type': 'SELL_TP', 'price': take_profit, 'capital': capital, 'time': timestamp})
                continue # Skip checking buy if we just sold or are holding
                
            # Check for Entry Condition if not in position
            if self.strategy.check_buy_signal(df, i):
                entry_price = close
                stop_loss, take_profit = self.strategy.calculate_exit_levels(df, i, entry_price)
                position = capital / entry_price
                print(f"[{timestamp}] BUY signal triggered at {entry_price:.2f}. SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                is_in_position = True
                trades.append({'type': 'BUY', 'price': entry_price, 'time': timestamp})
                
        # Close out any remaining position at end of test
        if is_in_position:
            final_price = df.iloc[-1]['close']
            capital = position * final_price
            trades.append({'type': 'SELL_END', 'price': final_price, 'capital': capital, 'time': df.iloc[-1]['timestamp']})
            
        print("\n--- Backtest Results ---")
        print(f"Total Trades: {len(trades) // 2}")
        print(f"Final Capital: ${capital:.2f}")
        return capital, trades

if __name__ == "__main__":
    tester = Backtester()
    tester.run()
