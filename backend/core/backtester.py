import pandas as pd
from core.data_fetcher import DataFetcher
from core.strategy import get_strategy
from core import config

class Backtester:
    def __init__(self, strategy_name="james_basic"):
        self.fetcher = DataFetcher()
        self.strategy = get_strategy(strategy_name)
        
    def run(self, symbol="BTC/KRW", timeframe="1h", limit=1000, initial_capital=1000000.0, start_date=None, end_date=None, db=None):
        if start_date:
            print(f"Running backtest on {symbol} {timeframe} from {start_date} to {end_date or 'now'}...")
        else:
            print(f"Running backtest on {symbol} {timeframe} for the last {limit} candles...")
            
        df = self.fetcher.fetch_ohlcv(symbol, timeframe, limit=limit, start_date=start_date, end_date=end_date, db=db)
        if df is None or len(df) == 0:
            return {"status": "error", "message": "No data fetched."}
            
        df = self.strategy.apply_indicators(df)
        
        capital = initial_capital
        position = 0.0     # Asset amount
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        is_in_position = False
        
        trades = []
        
        for i in range(1, len(df)):
            current_row = df.iloc[i]
            timestamp = current_row['timestamp']
            close = current_row['close']
            
            # Check for Exit Condition if in position
            if is_in_position:
                if current_row['low'] <= stop_loss:
                    old_capital = capital
                    # Realize the PnL on the position we held
                    capital_released = position * stop_loss
                    # For accounting, we keep 'capital' as the total liquid + equity? 
                    # In this simple model: capital is liquid cash.
                    # When we buy, capital decreases. When we sell, it increases.
                    # Wait, let's fix the capital tracking to be more intuitive.
                    pass 
                # (I will rewrite the loop logic below to be cleaner with risk-based sizing)
                pass

        # REWRITING LOOP FOR BETTER RISK MGMT
        liquid_capital = initial_capital
        position = 0.0
        is_in_position = False
        trades = []

        for i in range(2, len(df)):
            current_row = df.iloc[i]
            close = current_row['close']
            
            if is_in_position:
                # Exit Check
                exit_price = None
                reason = ""
                if current_row['low'] <= stop_loss:
                    exit_price = stop_loss
                    reason = "Stop Loss"
                elif current_row['high'] >= take_profit:
                    exit_price = take_profit
                    reason = "Take Profit"
                
                if exit_price:
                    pnl = (exit_price - entry_price) * position
                    liquid_capital += (position * exit_price) # Sell and get cash back
                    is_in_position = False
                    trades.append({
                        'side': 'SELL',
                        'price': exit_price,
                        'capital': liquid_capital,
                        'time': str(current_row['timestamp']),
                        'reason': reason,
                        'pnl': pnl
                    })
                    position = 0.0
                continue

            # Entry Check
            if self.strategy.check_buy_signal(df, i):
                entry_price = close
                sl, tp = self.strategy.calculate_exit_levels(df, i, entry_price)
                stop_loss = sl
                take_profit = tp
                
                # James's Risk Based Sizing:
                # Risk Amount = total_equity * 2%
                total_equity = liquid_capital
                risk_amount = total_equity * config.RISK_PER_TRADE
                price_risk = entry_price - stop_loss
                
                if price_risk > 0:
                    desired_position = risk_amount / price_risk
                    
                    # Safety: Can't buy more than we have cash for
                    max_position = liquid_capital / entry_price
                    position = min(desired_position, max_position)
                    
                    if position > 0:
                        liquid_capital -= (position * entry_price)
                        is_in_position = True
                        trades.append({
                            'side': 'BUY',
                            'price': entry_price,
                            'capital': liquid_capital + (position * entry_price), # Show total equity
                            'time': str(current_row['timestamp']),
                            'reason': 'Strategy Entry',
                            'pnl': 0
                        })

        # Final Close
        if is_in_position:
            final_price = df.iloc[-1]['close']
            pnl = (final_price - entry_price) * position
            liquid_capital += (position * final_price)
            trades.append({
                'side': 'SELL',
                'price': final_price,
                'capital': liquid_capital,
                'time': str(df.iloc[-1]['timestamp']),
                'reason': 'End of Test',
                'pnl': pnl
            })

        return {
            "status": "success",
            "initial_capital": initial_capital,
            "final_capital": liquid_capital,
            "total_trades": len(trades),
            "trades": trades
        }
