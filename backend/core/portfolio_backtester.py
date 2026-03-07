import pandas as pd
import numpy as np
from core.data_fetcher import DataFetcher
from core.strategy import get_strategy
from core import config
from sqlalchemy.orm import Session

class PortfolioBacktester:
    def __init__(self, strategy_name="james_basic"):
        self.fetcher = DataFetcher()
        self.strategy = get_strategy(strategy_name)

    def run(self, symbols: list, timeframe="1h", limit=1000, initial_capital=1000000.0, start_date=None, end_date=None, db: Session = None):
        print(f"Running portfolio backtest on {symbols} for the last {limit} candles...")
        
        # 1. Fetch data for all symbols
        dfs = {}
        for symbol in symbols:
            try:
                df = self.fetcher.fetch_ohlcv(symbol, timeframe, limit=limit, start_date=start_date, end_date=end_date, db=db)
                if df is not None and not df.empty:
                    dfs[symbol] = self.strategy.apply_indicators(df)
                    print(f"Loaded {len(dfs[symbol])} records for {symbol}")
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")

        if not dfs:
            return {"status": "error", "message": "No data fetched for any symbol."}

        # 2. Simulation State
        liquid_capital = initial_capital
        active_positions = {} # symbol -> {position, entry_price, stop_loss, take_profit}
        all_trades = []
        
        # 3. Synchronize Timestamps
        # Get all unique timestamps across all symbols, sorted
        all_timestamps = sorted(list(set().union(*(df['timestamp'].tolist() for df in dfs.values()))))
        
        # Map symbol -> timestamp -> row for fast lookup (using loc)
        # and also keep track of positional indices
        symbol_data_map = {s: df.set_index('timestamp') for s, df in dfs.items()}

        for ts in all_timestamps:
            # A. Check Exits and Update Trailing Stops
            symbols_to_exit = []
            for symbol, pos in active_positions.items():
                if ts not in symbol_data_map[symbol].index: continue
                current_row = symbol_data_map[symbol].loc[ts]
                curr_price = float(current_row['close'])
                
                # Check for Stop Loss / Take Profit
                exit_price = None
                reason = ""
                if current_row['low'] <= pos['stop_loss']:
                    exit_price = pos['stop_loss']
                    reason = "Stop Loss"
                elif current_row['high'] >= pos['take_profit']:
                    exit_price = pos['take_profit']
                    reason = "Take Profit"
                
                if exit_price:
                    pnl = (exit_price - pos['entry_price']) * pos['position']
                    liquid_capital += (pos['position'] * exit_price)
                    all_trades.append({
                        'symbol': symbol,
                        'side': 'SELL',
                        'price': float(exit_price),
                        'capital': float(liquid_capital),
                        'time': str(ts),
                        'reason': reason,
                        'pnl': float(pnl)
                    })
                    symbols_to_exit.append(symbol)
                else:
                    # Trailing Stop Update Logic
                    if hasattr(self.strategy, 'update_trailing_stop'):
                        atr = current_row.get('ATR_14', 0)
                        if atr > 0:
                            new_sl = self.strategy.update_trailing_stop(curr_price, atr, pos['stop_loss'])
                            pos['stop_loss'] = new_sl

            for s in symbols_to_exit:
                del active_positions[s]

            # B. Check Entries for all symbols NOT in position
            for symbol in symbols:
                if symbol in active_positions or symbol not in dfs: continue
                if ts not in symbol_data_map[symbol].index: continue
                
                original_df = dfs[symbol]
                
                # Get POSITIONAL index of this timestamp in original_df
                # This is more reliable for iloc and strategy checks
                matching_indices = np.where(original_df['timestamp'] == ts)[0]
                if len(matching_indices) == 0: continue
                current_idx = int(matching_indices[0])
                
                if current_idx < 10: continue # Need minimum warming up for indicators

                if self.strategy.check_buy_signal(original_df, current_idx):
                    entry_price = float(original_df.iloc[current_idx]['close'])
                    sl, tp = self.strategy.calculate_exit_levels(original_df, current_idx, entry_price)
                    
                    # Risk Management (2% of TOTAL EQUITY)
                    total_equity = liquid_capital
                    for s_pos, p_data in active_positions.items():
                        if ts in symbol_data_map[s_pos].index:
                            mkt_price = float(symbol_data_map[s_pos].loc[ts]['close'])
                            total_equity += (p_data['position'] * mkt_price)
                    
                    # Risk Management (2% of TOTAL EQUITY + Dynamic Multiplier)
                    risk_multiplier = 1.0
                    if hasattr(self.strategy, 'get_risk_multiplier'):
                        risk_multiplier = self.strategy.get_risk_multiplier(original_df, current_idx)
                    
                    risk_amount = total_equity * config.RISK_PER_TRADE * risk_multiplier
                    price_risk = entry_price - sl
                    
                    if price_risk > 0:
                        desired_qty = risk_amount / price_risk
                        max_qty = liquid_capital / entry_price
                        qty = min(desired_qty, max_qty)
                        
                        if qty > 0:
                            liquid_capital -= (qty * entry_price)
                            active_positions[symbol] = {
                                'position': qty,
                                'entry_price': entry_price,
                                'stop_loss': sl,
                                'take_profit': tp
                            }
                            all_trades.append({
                                'symbol': symbol,
                                'side': 'BUY',
                                'price': entry_price,
                                'capital': float(liquid_capital + (qty * entry_price)),
                                'time': str(ts),
                                'reason': 'Strategy Entry',
                                'pnl': 0.0
                            })

        # 4. Final Close Out at the very last available price for each
        final_equity = liquid_capital
        for symbol, pos in active_positions.items():
            if not dfs[symbol].empty:
                final_price = float(dfs[symbol].iloc[-1]['close'])
                pnl = (final_price - pos['entry_price']) * pos['position']
                final_equity += (pos['position'] * final_price)
                all_trades.append({
                    'symbol': symbol,
                    'side': 'SELL',
                    'price': final_price,
                    'capital': float(final_equity),
                    'time': str(dfs[symbol].iloc[-1]['timestamp']),
                    'reason': 'End of Test (Portfolio)',
                    'pnl': float(pnl)
                })

        return {
            "status": "success",
            "initial_capital": float(initial_capital),
            "final_capital": float(final_equity),
            "total_trades": len(all_trades),
            "trades": all_trades
        }

