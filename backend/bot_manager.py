import asyncio
import logging
import traceback
from typing import Dict, Any
from datetime import datetime
from core.data_fetcher import DataFetcher
from core.execution import ExecutionEngine
from core import config
from sqlalchemy.orm import Session
import database, models
from notifications import send_kakao_message
import pandas as pd

logger = logging.getLogger(__name__)

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
        db.rollback()
        logger.error("Failed to save trade log: %s", e)
    finally:
        db.close()


def _load_bot_config(bot_config_id: int) -> dict | None:
    """Load bot configuration from DB and return as a plain dict to avoid DetachedInstanceError."""
    db: Session = database.SessionLocal()
    try:
        bot_config = db.query(models.BotConfig).filter(models.BotConfig.id == bot_config_id).first()
        if not bot_config:
            logger.warning("[Bot %d] Bot configuration not found. Stopping.", bot_config_id)
            return None

        symbol_str = bot_config.symbol or "BTC/KRW"
        symbols = [s.strip() for s in symbol_str.split(',') if s.strip()]

        return {
            "symbols": symbols,
            "timeframe": bot_config.timeframe,
            "liquid_capital": bot_config.allocated_capital,
            "paper_trading": bot_config.paper_trading_mode,
            "strategy_name": getattr(bot_config, 'strategy_name', 'james_pro_stable'),
            "user_id": bot_config.user_id,
        }
    finally:
        db.close()


def _process_symbol_exit(
    symbol: str,
    pos: dict,
    curr_price: float,
    execution: ExecutionEngine,
    bot_config_id: int,
    user_id: int,
    liquid_capital: float,
) -> tuple[float, bool]:
    """
    Check stop-loss / take-profit and execute sell if triggered.
    Returns (updated_liquid_capital, was_exited).
    """
    exit_price = None
    reason = ""
    if curr_price <= pos['stop_loss']:
        exit_price = curr_price
        reason = "Stop Loss"
    elif curr_price >= pos['take_profit']:
        exit_price = curr_price
        reason = "Take Profit"

    if not exit_price:
        return liquid_capital, False

    logger.info("[Bot %d] %s hit for %s!", bot_config_id, reason.upper(), symbol)
    execution.execute_sell(symbol, exit_price, pos['position_amount'], reason=reason)
    pnl = (exit_price - pos['entry_price']) * pos['position_amount']
    liquid_capital += (pos['position_amount'] * exit_price)
    save_trade_log(bot_config_id, symbol, "SELL", exit_price, pos['position_amount'], f"{reason} (Portfolio)", pnl)

    # Send Kakao Notification -- safe percentage calculation
    cost_basis = pos['entry_price'] * pos['position_amount']
    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
    msg = (
        f"[SELL]\n"
        f"Symbol: {symbol}\n"
        f"Price: {exit_price:,.0f} KRW\n"
        f"PnL: {pnl_pct:.2f}%\n"
        f"Reason: {reason}"
    )
    _send_trade_notification(user_id, msg)

    return liquid_capital, True


def _process_symbol_entry(
    symbol: str,
    df: pd.DataFrame,
    curr_price: float,
    current_idx: int,
    strategy,
    execution: ExecutionEngine,
    bot_config_id: int,
    user_id: int,
    total_equity: float,
    liquid_capital: float,
) -> tuple[float, dict | None]:
    """
    Check buy signal and execute entry if triggered.
    Returns (updated_liquid_capital, new_position_dict_or_None).
    """
    if not strategy.check_buy_signal(df, current_idx):
        return liquid_capital, None

    logger.info("[Bot %d] *** BUY SIGNAL for %s! ***", bot_config_id, symbol)

    sl, tp = strategy.calculate_exit_levels(df, current_idx, curr_price)

    # Validate that exit levels are sensible (not NaN, SL < price < TP)
    if pd.isna(sl) or pd.isna(tp) or sl >= curr_price or tp <= curr_price:
        logger.warning(
            "[Bot %d] Invalid exit levels for %s: SL=%s, TP=%s, Price=%s. Skipping.",
            bot_config_id, symbol, sl, tp, curr_price,
        )
        return liquid_capital, None

    # Risk Management (2% of TOTAL Portfolio Equity)
    risk_multiplier = 1.0
    if hasattr(strategy, 'get_risk_multiplier'):
        risk_multiplier = strategy.get_risk_multiplier(df, current_idx)

    risk_amount = total_equity * config.RISK_PER_TRADE * risk_multiplier
    price_risk = curr_price - sl

    if price_risk <= 0:
        logger.warning("[Bot %d] Risk calculation failed for %s (risk <= 0)", bot_config_id, symbol)
        return liquid_capital, None

    desired_qty = risk_amount / price_risk
    max_qty = liquid_capital / curr_price if curr_price > 0 else 0
    qty = min(desired_qty, max_qty)

    if qty <= 0:
        return liquid_capital, None

    res = execution.execute_buy(symbol, curr_price, qty * curr_price)
    if not res or res["status"] != "success":
        return liquid_capital, None

    entry_price = res["price"]
    qty = res.get("amount", qty)
    liquid_capital -= (qty * entry_price)
    position = {
        'position_amount': qty,
        'entry_price': entry_price,
        'stop_loss': sl,
        'take_profit': tp,
    }
    save_trade_log(bot_config_id, symbol, "BUY", entry_price, qty, "Portfolio Entry")

    # Send Kakao Notification
    msg = (
        f"[BUY]\n"
        f"Symbol: {symbol}\n"
        f"Price: {entry_price:,.0f} KRW\n"
        f"Amount: {qty:.4f}\n"
        f"Status: Entry Complete"
    )
    _send_trade_notification(user_id, msg)

    return liquid_capital, position


def _send_trade_notification(user_id: int, msg: str) -> None:
    """Fire-and-forget Kakao notification wrapped in asyncio.create_task."""
    asyncio.create_task(send_kakao_message(user_id, msg))


async def run_bot_loop(bot_config_id: int):
    logger.info("--- [Bot %d] Engine Started (Portfolio Mode) ---", bot_config_id)
    fetcher = DataFetcher()

    cfg = _load_bot_config(bot_config_id)
    if cfg is None:
        return

    symbols = cfg["symbols"]
    timeframe = cfg["timeframe"]
    liquid_capital = cfg["liquid_capital"]
    paper_trading = cfg["paper_trading"]
    strategy_name = cfg["strategy_name"]
    user_id = cfg["user_id"]

    from core.strategy import get_strategy
    strategy = get_strategy(strategy_name)

    api_key = None
    api_secret = None
    exchange_name = 'upbit'

    if not paper_trading:
        db_new = database.SessionLocal()
        try:
            exchange_key = db_new.query(models.ExchangeKey).filter(models.ExchangeKey.user_id == user_id).first()
            if exchange_key:
                from crypto_utils import decrypt_key
                api_key = decrypt_key(exchange_key.api_key_encrypted)
                api_secret = decrypt_key(exchange_key.api_secret_encrypted)
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
    active_positions = {}  # symbol -> {position_amount, entry_price, stop_loss, take_profit}

    try:
        while True:
            logger.info("--- [Bot %d] Portfolio Tick: %d symbols ---", bot_config_id, len(symbols))

            # 1. Update Total Equity (Liquid + Current Positions Value)
            total_equity = liquid_capital
            current_prices = {}

            current_db = database.SessionLocal()
            try:
                # First pass: Fetch data for all symbols and update equity
                for symbol in symbols:
                    # Use async wrapper to avoid blocking the event loop with time.sleep()
                    df = await fetcher.fetch_ohlcv_async(symbol=symbol, timeframe=timeframe, limit=100, db=current_db)
                    if df is None or df.empty:
                        continue

                    curr_price = float(df.iloc[-1]['close'])
                    current_prices[symbol] = curr_price
                    if symbol in active_positions:
                        total_equity += (active_positions[symbol]['position_amount'] * curr_price)

                    # Process logic for this symbol
                    df = strategy.apply_indicators(df)
                    # Use iloc[-2] (last CLOSED candle) for all signal checks.
                    # iloc[-1] is the still-forming candle and must not be used for signals.
                    current_idx = len(df) - 2

                    # Guard: need at least 2 candles for current_idx >= 0, and strategies
                    # need current_idx >= 1 to access prev candle
                    if current_idx < 1:
                        continue

                    if symbol in active_positions:
                        pos = active_positions[symbol]

                        # A. Exit Check
                        liquid_capital, was_exited = _process_symbol_exit(
                            symbol, pos, curr_price, execution,
                            bot_config_id, user_id, liquid_capital,
                        )
                        if was_exited:
                            del active_positions[symbol]
                        else:
                            # B. Trailing Stop Update
                            if hasattr(strategy, 'update_trailing_stop'):
                                atr_val = df.iloc[current_idx].get('ATR_14', 0)
                                # Guard against NaN ATR which would corrupt the stop loss
                                if atr_val is not None and not pd.isna(atr_val) and atr_val > 0:
                                    new_sl = strategy.update_trailing_stop(curr_price, atr_val, pos['stop_loss'])
                                    if new_sl > pos['stop_loss']:
                                        pos['stop_loss'] = new_sl
                    else:
                        # C. Entry Check
                        liquid_capital, new_position = _process_symbol_entry(
                            symbol, df, curr_price, current_idx, strategy,
                            execution, bot_config_id, user_id,
                            total_equity, liquid_capital,
                        )
                        if new_position:
                            active_positions[symbol] = new_position

                logger.info(
                    "[Bot %d] Status: Equity=%s | Liquid=%s | Positions=%s",
                    bot_config_id,
                    f"{total_equity:,.0f}",
                    f"{liquid_capital:,.0f}",
                    list(active_positions.keys()),
                )

            except Exception as e:
                logger.error("[Bot %d] Loop error: %s", bot_config_id, e)
                logger.debug(traceback.format_exc())
            finally:
                current_db.close()

            # Sleep for 1 minute in portfolio mode to be more reactive
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("--- [Bot %d] Engine Stopped ---", bot_config_id)
        raise
    except Exception as e:
        logger.error("[Bot %d] Fatal error in bot loop: %s", bot_config_id, e)
        logger.debug(traceback.format_exc())
    finally:
        # Clean up from active_bots so status correctly reports Stopped
        active_bots.pop(bot_config_id, None)


def get_bot_status(bot_config_id: int):
    if bot_config_id in active_bots:
        task = active_bots[bot_config_id]
        if not task.done():
            return "Running"
    return "Stopped"
