import asyncio
from typing import Dict, Any
from datetime import datetime
from core.strategy import MomentumBreakoutStrategy
from core.data_fetcher import DataFetcher
from core.execution import ExecutionEngine
from core import config
from sqlalchemy.orm import Session
import database, models
from notifications import send_kakao_message

# Global dictionary to store currently running tasks (Simple In-Memory Queue)
# In production, use Celery + Redis for scaling.
active_bots: dict[int, asyncio.Task] = {}

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
    print(f"--- [Bot {bot_config_id}] Engine Started (Portfolio Mode) ---")
    fetcher = DataFetcher()
    
    db: Session = database.SessionLocal()
    bot_config = db.query(models.BotConfig).filter(models.BotConfig.id == bot_config_id).first()
    if not bot_config:
        print(f"[Bot {bot_config_id}] Bot configuration not found. Stopping.")
        db.close()
        return
    
    # Bot Configuration - Parse multiple symbols
    symbol_str = bot_config.symbol or "BTC/KRW"
    symbols = [s.strip() for s in symbol_str.split(',') if s.strip()]
    timeframe = bot_config.timeframe
    liquid_capital = bot_config.allocated_capital
    paper_trading = bot_config.paper_trading_mode
    strategy_name = getattr(bot_config, 'strategy_name', 'james_pro_stable')

    from core.strategy import get_strategy
    strategy = get_strategy(strategy_name)
    
    api_key = None
    api_secret = None
    exchange_name = 'upbit'

    db.close()

    if not paper_trading:
        db_new = database.SessionLocal()
        try:
            exchange_key = db_new.query(models.ExchangeKey).filter(models.ExchangeKey.user_id == bot_config.user_id).first()
            if exchange_key:
                from routers.keys import fake_encrypt 
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
    
    # Portfolio State
    active_positions = {} # symbol -> {position_amount, entry_price, stop_loss, take_profit}
    
    try:
        while True:
            print(f"--- [Bot {bot_config_id}] Portfolio Tick: {len(symbols)} symbols ---")
            
            # 1. Update Total Equity (Liquid + Current Positions Value)
            total_equity = liquid_capital
            current_prices = {}
            
            current_db = database.SessionLocal()
            try:
                # First pass: Fetch data for all symbols and update equity
                for symbol in symbols:
                    df = fetcher.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=100, db=current_db)
                    if df is not None and not df.empty:
                        curr_price = float(df.iloc[-1]['close'])
                        current_prices[symbol] = curr_price
                        if symbol in active_positions:
                            total_equity += (active_positions[symbol]['position_amount'] * curr_price)
                        
                        # Process logic for this symbol
                        df = strategy.apply_indicators(df)
                        current_idx = len(df) - 1
                        
                        if symbol in active_positions:
                            pos = active_positions[symbol]
                            # A. Exit Check
                            exit_price = None
                            reason = ""
                            if curr_price <= pos['stop_loss']:
                                exit_price = curr_price
                                reason = "Stop Loss"
                            elif curr_price >= pos['take_profit']:
                                exit_price = curr_price
                                reason = "Take Profit"

                            if exit_price:
                                print(f"[Bot {bot_config_id}] {reason.upper()} hit for {symbol}!")
                                res = execution.execute_sell(symbol, exit_price, pos['position_amount'], reason=reason)
                                pnl = (exit_price - pos['entry_price']) * pos['position_amount']
                                liquid_capital += (pos['position_amount'] * exit_price)
                                save_trade_log(bot_config_id, symbol, "SELL", exit_price, pos['position_amount'], f"{reason} (Portfolio)", pnl)
                                
                                # Send Kakao Notification
                                msg = f"🔔 [거래 알림 - SELL]\n종목: {symbol}\n가격: {exit_price:,.0f} KRW\n수익률: {(pnl / (pos['entry_price'] * pos['position_amount']) * 100):.2f}%\n사유: {reason}"
                                asyncio.create_task(send_kakao_message(bot_config.user_id, msg))
                                
                                del active_positions[symbol]
                            else:
                                # B. Trailing Stop Update
                                if hasattr(strategy, 'update_trailing_stop'):
                                    atr = df.iloc[current_idx].get('ATR_14', 0)
                                    if atr > 0:
                                        new_sl = strategy.update_trailing_stop(curr_price, atr, pos['stop_loss'])
                                        if new_sl > pos['stop_loss']:
                                            pos['stop_loss'] = new_sl
                        else:
                            # C. Entry Check
                            if strategy.check_buy_signal(df, current_idx):
                                print(f"[Bot {bot_config_id}] *** BUY SIGNAL for {symbol}! ***")
                                
                                sl, tp = strategy.calculate_exit_levels(df, current_idx, curr_price)
                                
                                # Risk Management (2% of TOTAL Portfolio Equity)
                                risk_multiplier = 1.0
                                if hasattr(strategy, 'get_risk_multiplier'):
                                    risk_multiplier = strategy.get_risk_multiplier(df, current_idx)
                                
                                risk_amount = total_equity * config.RISK_PER_TRADE * risk_multiplier
                                price_risk = curr_price - sl
                                
                                if price_risk > 0:
                                    desired_qty = risk_amount / price_risk
                                    max_qty = liquid_capital / curr_price
                                    qty = min(desired_qty, max_qty)
                                    
                                    if qty > 0:
                                        res = execution.execute_buy(symbol, curr_price, qty * curr_price)
                                        if res and res["status"] == "success":
                                            entry_price = res["price"]
                                            qty = res.get("amount", qty)
                                            liquid_capital -= (qty * entry_price)
                                            active_positions[symbol] = {
                                                'position_amount': qty,
                                                'entry_price': entry_price,
                                                'stop_loss': sl,
                                                'take_profit': tp
                                            }
                                            save_trade_log(bot_config_id, symbol, "BUY", entry_price, qty, "Portfolio Entry")
                                            
                                            # Send Kakao Notification
                                            msg = f"🚀 [거래 알림 - BUY]\n종목: {symbol}\n가격: {entry_price:,.0f} KRW\n수량: {qty:.4f}\n상태: 진입 완료"
                                            asyncio.create_task(send_kakao_message(bot_config.user_id, msg))
                                else:
                                    print(f"[Bot {bot_config_id}] Risk calculation failed for {symbol} (risk <= 0)")
                
                print(f"[Bot {bot_config_id}] Status: Equity={total_equity:,.0f} | Liquid={liquid_capital:,.0f} | Positions={list(active_positions.keys())}")
                
            except Exception as e:
                print(f"[Bot {bot_config_id}] Loop error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                current_db.close()
            
            # Sleep for 1 minute in portfolio mode to be more reactive
            await asyncio.sleep(60)
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
