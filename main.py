import time
import schedule
import config
from data_fetcher import DataFetcher
from strategy import MomentumBreakoutStrategy
from execution import ExecutionEngine

class TradingBot:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.strategy = MomentumBreakoutStrategy()
        self.execution = ExecutionEngine(paper_trading=True)
        
        self.is_in_position = False
        self.position_amount = 0.0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.capital = 1000.0 # Starting mock capital
        
    def tick(self):
        print(f"\n--- Bot Tick: Fetching data for {config.SYMBOL} {config.TIMEFRAME} ---")
        df = self.fetcher.fetch_ohlcv()
        if df is None or len(df) == 0:
            print("Failed to fetch data.")
            return
            
        df = self.strategy.apply_indicators(df)
        current_idx = len(df) - 1
        current_row = df.iloc[current_idx]
        current_price = current_row['close']
        
        print(f"Current Price: {current_price:.2f}")

        if self.is_in_position:
            # Check exit conditions based on live prices
            if current_price <= self.stop_loss:
                print("STOP LOSS hit!")
                self.execution.execute_sell(config.SYMBOL, current_price, self.position_amount, reason="Stop Loss")
                self.is_in_position = False
            elif current_price >= self.take_profit:
                print("TAKE PROFIT hit!")
                self.execution.execute_sell(config.SYMBOL, current_price, self.position_amount, reason="Take Profit")
                self.is_in_position = False
            else:
                print(f"Holding position. Cur: {current_price:.2f} / SL: {self.stop_loss:.2f} / TP: {self.take_profit:.2f}")
        else:
            # Check entry conditions
            if self.strategy.check_buy_signal(df, current_idx):
                print(f"*** JAMES MOMENTUM BREAKOUT SIGNAL TRIGGERED! ***")
                # Execute buy order
                res = self.execution.execute_buy(config.SYMBOL, current_price, self.capital)
                if res and res["status"] == "success":
                    self.is_in_position = True
                    self.entry_price = res["price"]
                    self.position_amount = res["amount"]
                    self.stop_loss, self.take_profit = self.strategy.calculate_exit_levels(df, current_idx, self.entry_price)
                    print(f"New Position active -> Entry: {self.entry_price:.2f}, SL: {self.stop_loss:.2f}, TP: {self.take_profit:.2f}")
            else:
                print("No buy signal currently.")

def run_scheduler():
    bot = TradingBot()
    bot.tick() # Run once immediately
    
    # 1시간봉 전략이므로 너무 자주 확인할 필요 없이 매 5분 마다 최신 봉 갱신 및 체결 확인
    schedule.every(5).minutes.do(bot.tick)
    
    print("Scheduler running... Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
