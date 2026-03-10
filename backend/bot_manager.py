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

# ──────────────────────────────────────────────
# 리스크 관리 상수
# ──────────────────────────────────────────────
MAX_CONCURRENT_POSITIONS = 3          # 최대 동시 포지션 수
MAX_RISK_MULTIPLIER = 2.0             # 리스크 배수 상한 (자산 대비 최대 4%)
STOP_LOSS_COOLDOWN_SECONDS = 3600     # 손절 후 재진입 금지 시간 (1시간)


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


# ──────────────────────────────────────────────
# 포지션 영속화 (서버 재시작 시 복구용)
# ──────────────────────────────────────────────

def save_positions_to_db(bot_id: int, active_positions: dict) -> None:
    """현재 보유 포지션을 DB에 저장 (upsert)"""
    db: Session = database.SessionLocal()
    try:
        # 기존 포지션 삭제 후 새로 삽입
        db.query(models.ActivePosition).filter(models.ActivePosition.bot_id == bot_id).delete()
        for symbol, pos in active_positions.items():
            db.add(models.ActivePosition(
                bot_id=bot_id,
                symbol=symbol,
                position_amount=pos['position_amount'],
                entry_price=pos['entry_price'],
                stop_loss=pos['stop_loss'],
                take_profit=pos['take_profit'],
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("[Bot %d] Failed to save positions: %s", bot_id, e)
    finally:
        db.close()


def load_positions_from_db(bot_id: int) -> dict:
    """DB에서 포지션 복구"""
    db: Session = database.SessionLocal()
    positions = {}
    try:
        rows = db.query(models.ActivePosition).filter(
            models.ActivePosition.bot_id == bot_id
        ).all()
        for row in rows:
            positions[row.symbol] = {
                'position_amount': row.position_amount,
                'entry_price': row.entry_price,
                'stop_loss': row.stop_loss,
                'take_profit': row.take_profit,
            }
        if positions:
            logger.info("[Bot %d] Recovered %d positions from DB", bot_id, len(positions))
    except Exception as e:
        logger.error("[Bot %d] Failed to load positions: %s", bot_id, e)
    finally:
        db.close()
    return positions


def clear_positions_from_db(bot_id: int) -> None:
    """봇 정지 시 DB 포지션 정리"""
    db: Session = database.SessionLocal()
    try:
        db.query(models.ActivePosition).filter(models.ActivePosition.bot_id == bot_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("[Bot %d] Failed to clear positions: %s", bot_id, e)
    finally:
        db.close()


# ──────────────────────────────────────────────
# 봇 활성 상태 DB 동기화
# ──────────────────────────────────────────────

def set_bot_active(bot_id: int, active: bool) -> None:
    """DB의 is_active 플래그를 업데이트"""
    db: Session = database.SessionLocal()
    try:
        bot = db.query(models.BotConfig).filter(models.BotConfig.id == bot_id).first()
        if bot:
            bot.is_active = active
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error("[Bot %d] Failed to update is_active: %s", bot_id, e)
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
    sell_result = execution.execute_sell(symbol, exit_price, pos['position_amount'], reason=reason)

    # 실매매에서 매도 실패 시 포지션 유지 (강제 청산하지 않음)
    if not sell_result or sell_result["status"] != "success":
        logger.error("[Bot %d] SELL FAILED for %s. Keeping position.", bot_config_id, symbol)
        return liquid_capital, False

    # 실제 체결가 사용 (슬리피지/시장가 반영)
    actual_price = sell_result.get("price", exit_price)
    actual_amount = sell_result.get("amount", pos['position_amount'])
    pnl = (actual_price - pos['entry_price']) * actual_amount
    liquid_capital += (actual_amount * actual_price)
    save_trade_log(bot_config_id, symbol, "SELL", actual_price, actual_amount, f"{reason} (Portfolio)", pnl)

    # Send Kakao Notification
    cost_basis = pos['entry_price'] * pos['position_amount']
    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
    msg = (
        f"[SELL]\n"
        f"Symbol: {symbol}\n"
        f"Price: {actual_price:,.0f} KRW\n"
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
    # 리스크 배수 상한 적용
    risk_multiplier = min(risk_multiplier, MAX_RISK_MULTIPLIER)

    risk_amount = total_equity * config.RISK_PER_TRADE * risk_multiplier
    price_risk = curr_price - sl

    if price_risk <= 0:
        logger.warning("[Bot %d] Risk calculation failed for %s (risk <= 0)", bot_config_id, symbol)
        return liquid_capital, None

    desired_qty = risk_amount / price_risk
    max_qty = liquid_capital / curr_price if curr_price > 0 else 0
    qty = min(desired_qty, max_qty)

    if qty <= 0 or liquid_capital <= 0:
        return liquid_capital, None

    # 매수 금액이 유동 자본을 초과하지 않도록 보장
    buy_amount = min(qty * curr_price, liquid_capital)
    qty = buy_amount / curr_price
    if qty <= 0:
        return liquid_capital, None

    res = execution.execute_buy(symbol, curr_price, buy_amount)
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
        set_bot_active(bot_config_id, False)
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
                logger.error("[Bot %d] No API key found for user %d. Cannot start live trading.", bot_config_id, user_id)
                set_bot_active(bot_config_id, False)
                return
        finally:
            db_new.close()

    execution = ExecutionEngine(
        api_key=api_key,
        api_secret=api_secret,
        exchange_name=exchange_name,
        paper_trading=paper_trading
    )

    # 실매매 모드인데 거래소 연결 실패 시 봇 정지
    if not paper_trading and not execution.is_live_ready():
        logger.error("[Bot %d] Exchange connection failed. Stopping bot.", bot_config_id)
        set_bot_active(bot_config_id, False)
        return

    # Portfolio State — DB에서 복구 시도
    active_positions = load_positions_from_db(bot_config_id)
    # 손절 쿨다운 추적: {symbol: datetime}
    cooldown_until: dict[str, datetime] = {}

    # 포지션이 복구된 경우, liquid_capital에서 보유 금액 차감
    for sym, pos in active_positions.items():
        invested = pos['entry_price'] * pos['position_amount']
        liquid_capital -= invested
        logger.info("[Bot %d] Recovered position %s: entry=%.0f, qty=%.4f", bot_config_id, sym, pos['entry_price'], pos['position_amount'])

    # DB에 활성 상태 표시
    set_bot_active(bot_config_id, True)

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10  # 연속 10회 에러 시 봇 중단

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
                    df = await fetcher.fetch_ohlcv_async(symbol=symbol, timeframe=timeframe, limit=300, db=current_db)
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
                            # 손절인 경우 쿨다운 적용
                            if curr_price <= pos['stop_loss']:
                                from datetime import timedelta
                                cooldown_until[symbol] = datetime.now() + timedelta(seconds=STOP_LOSS_COOLDOWN_SECONDS)
                                logger.info("[Bot %d] %s cooldown until %s after stop loss", bot_config_id, symbol, cooldown_until[symbol])
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
                        # C. Entry Check (포지션 수 제한 + 쿨다운 체크)
                        if len(active_positions) >= MAX_CONCURRENT_POSITIONS:
                            pass  # 최대 포지션 도달, 진입 스킵
                        elif symbol in cooldown_until and datetime.now() < cooldown_until[symbol]:
                            pass  # 손절 쿨다운 중, 진입 스킵
                        else:
                            liquid_capital, new_position = _process_symbol_entry(
                                symbol, df, curr_price, current_idx, strategy,
                                execution, bot_config_id, user_id,
                                total_equity, liquid_capital,
                            )
                            if new_position:
                                active_positions[symbol] = new_position
                                # 쿨다운 만료된 항목 정리
                                cooldown_until.pop(symbol, None)

                # 매 tick마다 포지션 상태를 DB에 저장
                save_positions_to_db(bot_config_id, active_positions)

                logger.info(
                    "[Bot %d] Status: Equity=%s | Liquid=%s | Positions=%s",
                    bot_config_id,
                    f"{total_equity:,.0f}",
                    f"{liquid_capital:,.0f}",
                    list(active_positions.keys()),
                )

                consecutive_errors = 0  # 성공 시 에러 카운터 초기화

            except Exception as e:
                consecutive_errors += 1
                logger.error("[Bot %d] Loop error (%d/%d): %s", bot_config_id, consecutive_errors, MAX_CONSECUTIVE_ERRORS, e)
                logger.debug(traceback.format_exc())
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error("[Bot %d] Too many consecutive errors. Stopping bot.", bot_config_id)
                    # 에러로 중단해도 포지션은 DB에 저장
                    save_positions_to_db(bot_config_id, active_positions)
                    break
            finally:
                current_db.close()

            # 에러가 연속되면 대기 시간을 늘림 (최대 5분)
            sleep_time = min(60 * (1 + consecutive_errors), 300)
            await asyncio.sleep(sleep_time)
    except asyncio.CancelledError:
        logger.info("--- [Bot %d] Engine Stopped (graceful) ---", bot_config_id)
        # 포지션은 DB에 유지 (재시작 시 복구 가능)
        save_positions_to_db(bot_config_id, active_positions)
        raise
    except Exception as e:
        logger.error("[Bot %d] Fatal error in bot loop: %s", bot_config_id, e)
        logger.debug(traceback.format_exc())
    finally:
        # Clean up from active_bots so status correctly reports Stopped
        active_bots.pop(bot_config_id, None)
        set_bot_active(bot_config_id, False)


def get_bot_status(bot_config_id: int):
    if bot_config_id in active_bots:
        task = active_bots[bot_config_id]
        if not task.done():
            return "Running"
    return "Stopped"


# ──────────────────────────────────────────────
# 서버 시작 시 봇 자동 복구 & Graceful Shutdown
# ──────────────────────────────────────────────

async def recover_active_bots() -> None:
    """서버 시작 시 DB에서 is_active=True인 봇을 자동 재가동"""
    db: Session = database.SessionLocal()
    try:
        active_bot_configs = db.query(models.BotConfig).filter(
            models.BotConfig.is_active == True,
        ).all()

        if not active_bot_configs:
            logger.info("[Recovery] No active bots to recover.")
            return

        for bot_cfg in active_bot_configs:
            bot_id = bot_cfg.id
            paper_label = "모의투자" if bot_cfg.paper_trading_mode else "실매매"
            logger.info(
                "[Recovery] Restarting bot %d (%s, %s, %s)",
                bot_id, bot_cfg.symbol, bot_cfg.strategy_name, paper_label,
            )
            task = asyncio.create_task(run_bot_loop(bot_id))
            active_bots[bot_id] = task

        logger.info("[Recovery] Recovered %d bot(s).", len(active_bot_configs))
    except Exception as e:
        logger.error("[Recovery] Failed to recover bots: %s", e)
    finally:
        db.close()


async def graceful_shutdown() -> None:
    """서버 종료 시 모든 봇을 안전하게 중단 (포지션은 DB에 유지)"""
    if not active_bots:
        return

    logger.info("[Shutdown] Stopping %d active bot(s)...", len(active_bots))

    tasks = list(active_bots.values())
    for task in tasks:
        task.cancel()

    # 모든 태스크가 종료될 때까지 대기 (최대 10초)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.error("[Shutdown] Bot task error: %s", result)

    logger.info("[Shutdown] All bots stopped. Positions preserved in DB.")
