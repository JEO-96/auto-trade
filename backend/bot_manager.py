import asyncio
from typing import Dict
from datetime import datetime
from core.strategy import MomentumBreakoutStrategy
from core.data_fetcher import DataFetcher
from core.execution import ExecutionEngine
from core import config
from sqlalchemy.orm import Session
import database, models

# Global dictionary to store currently running tasks (Simple In-Memory Queue)
# In production, use Celery + Redis for scaling.
active_bots: Dict[int, asyncio.Task] = {}

def save_trade_log(bot_id: int, symbol: str, side: str, price: float, amount: float, reason: str, pnl: float = None):
    db: Session = database.SessionLocal()
    try:
        log = models.TradeLog(
            bot_id=bot_id,
            symbol=symbol,
            side=side,
            price=price,
            amount=amount,
            pnl=pnl,
            reason=reason,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Failed to save trade log: {e}")
    finally:
        db.close()

async def run_bot_loop(bot_config_id: int):
    print(f"--- [Bot {bot_config_id}] Engine Started ---")
    fetcher = DataFetcher()
    strategy = MomentumBreakoutStrategy()
    
    db: Session = database.SessionLocal()
    bot_config = db.query(models.BotConfig).filter(models.BotConfig.id == bot_config_id).first()
    if not bot_config:
        print(f"[Bot {bot_config_id}] Bot configuration not found. Stopping.")
        db.close()
        return
    
    # Bot Configuration
    symbol = bot_config.symbol
    timeframe = bot_config.timeframe
    capital = bot_config.allocated_capital
    paper_trading = bot_config.paper_trading_mode

    # Use Strategy Factory
    from core.strategy import get_strategy
    # Now defaulting to 'james_pro_stable' as the 'Standard' version was retired.
    strategy_name = getattr(bot_config, 'strategy_name', 'james_pro_stable')
    strategy = get_strategy(strategy_name)
    
    # Setup Execution Engine
    api_key = None
    api_secret = None
    exchange_name = 'upbit'

    # Need careful session management inside a long-running task
    # We close the initial session and open new ones when needed
    db.close()

    if not paper_trading:
        db_new = database.SessionLocal()
        try:
            exchange_key = db_new.query(models.ExchangeKey).filter(models.ExchangeKey.user_id == bot_config.user_id).first()
            if exchange_key:
                from main import fake_encrypt 
                api_key = fake_encrypt(exchange_key.api_key_encrypted) 
                api_secret = fake_encrypt(exchange_key.api_secret_encrypted)
                exchange_name = exchange_key.exchange_name
            else:
                paper_trading = True
        finally:
            db_new.close()

    execution = ExecutionEngine(
        api_key=api_key, 
        api_secret=api_secret, 
        exchange_name=exchange_name, 
        paper_trading=paper_trading
    )
    
    is_in_position = False
    position_amount = 0.0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    try:
        while True:
            print(f"--- [Bot {bot_config_id} | {symbol}] Tick: Fetching data... ---")
            
            # Use a fresh DB session for caching
            current_db = database.SessionLocal()
            try:
                df = fetcher.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=200, db=current_db)
                
                if df is not None and len(df) > 0:
                    df = strategy.apply_indicators(df)
                    current_idx = len(df) - 1
                    current_price = df.iloc[current_idx]['close']
                    
                    if is_in_position:
                        # 1. Exit Check: Stop Loss or Take Profit
                        exit_price = None
                        reason = ""
                        if current_price <= stop_loss:
                            exit_price = current_price
                            reason = "Stop Loss"
                        elif current_price >= take_profit:
                            exit_price = current_price
                            reason = "Take Profit"

                        if exit_price:
                            print(f"[Bot {bot_config_id}] {reason.upper()} hit for {symbol}!")
                            res = execution.execute_sell(symbol, exit_price, position_amount, reason=reason)
                            pnl = (exit_price - entry_price) * position_amount
                            save_trade_log(bot_config_id, symbol, "SELL", exit_price, position_amount, f"{reason} (Elite)", pnl)
                            is_in_position = False
                        else:
                            # 2. Trailing Stop Update (Elite Feature)
                            if hasattr(strategy, 'update_trailing_stop'):
                                atr = df.iloc[current_idx].get('ATR_14', 0)
                                if atr > 0:
                                    new_sl = strategy.update_trailing_stop(current_price, atr, stop_loss)
                                    if new_sl > stop_loss:
                                        stop_loss = new_sl
                                        # Optional: print(f"[Bot {bot_config_id}] Trailing SL updated: {stop_loss}")
                    else:
                        if strategy.check_buy_signal(df, current_idx):
                            print(f"[Bot {bot_config_id}] *** SIGNAL TRIGGERED for {symbol}! ***")
                            
                            # Calculate Stop Loss and Take Profit BEFORE buying
                            sl, tp = strategy.calculate_exit_levels(df, current_idx, current_price)
                            
                            # James's Risk Based Sizing
                            # Risk 2% of allocated capital
                            risk_amount = capital * config.RISK_PER_TRADE
                            price_risk = current_price - sl
                            
                            if price_risk > 0:
                                desired_amount = risk_amount / price_risk
                                # Max allowed amount based on allocated capital
                                max_amount = capital / current_price
                                position_amount = min(desired_amount, max_amount)
                                
                                if position_amount > 0:
                                    res = execution.execute_buy(symbol, current_price, position_amount * current_price)
                                    if res and res["status"] == "success":
                                        is_in_position = True
                                        entry_price = res["price"]
                                        # Use actual filled amount if available, else ours
                                        position_amount = res.get("amount", position_amount)
                                        stop_loss = sl
                                        take_profit = tp
                                        save_trade_log(bot_config_id, symbol, "BUY", entry_price, position_amount, "Strategy Entry (Risk Adjusted)")
                            else:
                                print(f"[Bot {bot_config_id}] WARNING: Price risk is 0 or negative. Skipping trade.")
            except Exception as e:
                print(f"[Bot {bot_config_id}] Loop error: {e}")
            finally:
                current_db.close()
            
            # Sleep for 5 minutes before checking again
            await asyncio.sleep(300)
    except asyncio.CancelledError:
        print(f"--- [Bot {bot_config_id}] Engine Stopped ---")
        raise
    except Exception as e:
        print(f"[Bot {bot_config_id}] Error in bot loop: {e}")

def get_bot_status(bot_config_id: int):
    if bot_config_id in active_bots:
        task = active_bots[bot_config_id]
        if not task.done():
            return "Running"
    return "Stopped"
