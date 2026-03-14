import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Optional

import pandas as pd

import database
import models
from constants import (
    MAX_CONCURRENT_POSITIONS,
    MAX_CONSECUTIVE_ERRORS,
    MAX_RISK_MULTIPLIER,
    STOP_LOSS_COOLDOWN_SECONDS,
    STRATEGY_LABELS,
)
from core import config
from core.data_fetcher import DataFetcher
from core.execution import ExecutionEngine
from notifications import send_telegram_message, send_trade_notification, send_bot_status_notification

# ──────────────────────────────────────────────
# 분리된 모듈에서 임포트 + 하위 호환성을 위한 재수출
# ──────────────────────────────────────────────
from position_manager import (  # noqa: F401 — re-exported for backward compatibility
    clear_positions_from_db,
    load_positions_from_db,
    save_positions_to_db,
    set_bot_active,
)
from trade_logger import save_trade_log  # noqa: F401 — re-exported for backward compatibility
from utils import parse_symbols

logger = logging.getLogger(__name__)

# Global dictionary to store currently running tasks (Simple In-Memory Queue)
# In production, use Celery + Redis for scaling.
active_bots: dict[int, asyncio.Task] = {}

# 서버 셧다운 중 플래그 — True이면 finally 블록에서 is_active=False 설정을 건너뜀
_shutting_down: bool = False



def _load_bot_config(bot_config_id: int) -> Optional[dict]:
    """Load bot configuration from DB and return as a plain dict to avoid DetachedInstanceError."""
    with database.get_db_session() as db:
        bot_config = db.query(models.BotConfig).filter(models.BotConfig.id == bot_config_id).first()
        if not bot_config:
            logger.warning("[Bot %d] Bot configuration not found. Stopping.", bot_config_id)
            return None

        symbols = parse_symbols(bot_config.symbol or "BTC/KRW")

        return {
            "symbols": symbols,
            "timeframe": bot_config.timeframe,
            "liquid_capital": bot_config.allocated_capital,
            "paper_trading": bot_config.paper_trading_mode,
            "strategy_name": getattr(bot_config, 'strategy_name', 'james_pro_stable'),
            "exchange_name": getattr(bot_config, 'exchange_name', 'upbit'),
            "user_id": bot_config.user_id,
        }


def _process_symbol_exit(
    symbol: str,
    pos: dict,
    curr_price: float,
    execution: ExecutionEngine,
    bot_config_id: int,
    user_id: int,
    liquid_capital: float,
    paper_trading: bool = True,
) -> tuple[float, bool]:
    """
    Check stop-loss / take-profit and execute sell if triggered.
    Returns (updated_liquid_capital, was_exited).
    """
    exit_price: Optional[float] = None
    reason: str = ""
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
    actual_price: float = sell_result.get("price", exit_price)
    actual_amount: float = sell_result.get("amount", pos['position_amount'])
    pnl: float = (actual_price - pos['entry_price']) * actual_amount
    liquid_capital += (actual_amount * actual_price)
    save_trade_log(bot_config_id, symbol, "SELL", actual_price, actual_amount, f"{reason} (Portfolio)", pnl)

    # 실매매인 경우 크레딧 처리
    if not paper_trading and pnl != 0:
        import credit_service
        credit_service.process_trade_pnl(user_id, pnl)

    cost_basis: float = pos['entry_price'] * pos['position_amount']
    pnl_pct: float = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    reason_kr = {"Stop Loss": "손절", "Take Profit": "익절"}.get(reason, reason)
    msg = (
        f"📉 [매도]\n"
        f"종목: {symbol}\n"
        f"체결가: {actual_price:,.0f} KRW\n"
        f"{pnl_emoji} 손익: {pnl_pct:+.2f}% ({pnl:+,.0f} KRW)\n"
        f"사유: {reason_kr}"
    )
    _send_trade_notification(user_id, msg)

    return liquid_capital, True


def _process_symbol_entry(
    symbol: str,
    df: pd.DataFrame,
    curr_price: float,
    current_idx: int,
    strategy: Any,
    execution: ExecutionEngine,
    bot_config_id: int,
    user_id: int,
    total_equity: float,
    liquid_capital: float,
) -> tuple[float, Optional[dict]]:
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

    # 백테스트와 동일: 가용 자본 100% 사용
    if liquid_capital <= 0 or curr_price <= 0:
        return liquid_capital, None

    buy_amount: float = liquid_capital
    qty: float = buy_amount / curr_price
    if qty <= 0:
        return liquid_capital, None

    res = execution.execute_buy(symbol, curr_price, buy_amount)
    if not res or res["status"] != "success":
        return liquid_capital, None

    entry_price: float = res["price"]
    qty = res.get("amount", qty)
    liquid_capital -= (qty * entry_price)
    position: dict = {
        'position_amount': qty,
        'entry_price': entry_price,
        'stop_loss': sl,
        'take_profit': tp,
    }
    save_trade_log(bot_config_id, symbol, "BUY", entry_price, qty, "Portfolio Entry")

    msg = (
        f"📈 [매수]\n"
        f"종목: {symbol}\n"
        f"체결가: {entry_price:,.0f} KRW\n"
        f"수량: {qty:.4f}\n"
        f"상태: 진입 완료"
    )
    _send_trade_notification(user_id, msg)

    return liquid_capital, position


def _send_trade_notification(user_id: int, msg: str) -> None:
    """Fire-and-forget trade notification wrapped in asyncio.create_task."""
    asyncio.create_task(send_trade_notification(user_id, msg))


def _send_bot_status_notification(user_id: int, msg: str) -> None:
    """Fire-and-forget bot status notification wrapped in asyncio.create_task."""
    asyncio.create_task(send_bot_status_notification(user_id, msg))


# 타임프레임별 캔들 마감 간격 (분)
_TIMEFRAME_MINUTES: dict[str, int] = {
    '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
    '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480,
    '12h': 720, '1d': 1440, '1w': 10080,
}

def _get_nearest_candle_close(timeframe: str) -> int:
    """현재 시각에서 가장 가까운 캔들 마감 시각(분)을 반환.
    tolerance 범위 내에서 마감 전/후 모두 같은 값을 반환하여 중복 알림 방지.
    예: 1h봉, 4:58 → 300(=5시), 5:01 → 300(=5시)
    """
    interval = _TIMEFRAME_MINUTES.get(timeframe, 0)
    if interval <= 0:
        return -1
    now = datetime.now()
    minutes_since_midnight = now.hour * 60 + now.minute
    # 가장 가까운 마감 시각 = interval의 배수 중 현재 시각에 가장 가까운 것
    lower = (minutes_since_midnight // interval) * interval
    upper = lower + interval
    if (minutes_since_midnight - lower) <= (upper - minutes_since_midnight):
        return lower
    return upper


def _is_candle_close_time(timeframe: str, tolerance_minutes: int = 2) -> bool:
    """현재 시각이 캔들 마감 시점 근처(±tolerance)인지 확인.
    예: 4h봉이면 0시, 4시, 8시, 12시, 16시, 20시 (KST) 전후 2분."""
    interval = _TIMEFRAME_MINUTES.get(timeframe, 0)
    if interval <= 0:
        return True  # 알 수 없는 타임프레임이면 항상 전송

    now = datetime.now()
    minutes_since_midnight = now.hour * 60 + now.minute
    # 자정(00:00) 기준으로 캔들 마감 시각은 interval의 배수
    remainder = minutes_since_midnight % interval
    # remainder가 0 근처이거나 interval 근처이면 마감 시점
    return remainder <= tolerance_minutes or (interval - remainder) <= tolerance_minutes


def _build_tick_feedback(
    signal_details: list[str],
    paper_trading: bool,
    strategy_name: str,
    timeframe: str,
    total_equity: float,
    real_balance_krw: float | None = None,
) -> str:
    """매 tick 카카오 피드백 메시지 생성."""
    mode_label = "모의투자" if paper_trading else "실매매"
    now_str = datetime.now().strftime("%m/%d %H:%M")
    strategy_label = STRATEGY_LABELS.get(strategy_name, strategy_name)

    # 실매매: 실제 업비트 잔고 표시 / 모의투자: 봇 내부 추적 자산 표시
    if not paper_trading and real_balance_krw is not None:
        asset_line = f"💰 업비트 자산: {real_balance_krw:,.0f} KRW"
    else:
        asset_line = f"💰 자산: {total_equity:,.0f} KRW"

    return (
        f"📈 [{mode_label}] {strategy_label}\n"
        f"⏰ {now_str} | {timeframe}봉 분석\n"
        f"{asset_line}\n"
        f"{'─' * 24}\n"
        + f"\n{'─' * 24}\n".join(signal_details)
    )


def _initialize_bot_engine(bot_config_id: int) -> Optional[dict]:
    """봇 루프 시작에 필요한 설정, 전략, 실행 엔진, 포지션을 초기화.
    실패 시 None 반환, 성공 시 초기화된 상태 dict 반환."""
    cfg = _load_bot_config(bot_config_id)
    if cfg is None:
        set_bot_active(bot_config_id, False)
        return None

    symbols: list[str] = cfg["symbols"]
    liquid_capital: float = cfg["liquid_capital"]
    paper_trading: bool = cfg["paper_trading"]
    user_id: int = cfg["user_id"]

    from core.strategy import get_strategy
    strategy = get_strategy(cfg["strategy_name"])

    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    exchange_name: str = cfg.get("exchange_name", "upbit") or "upbit"

    if not paper_trading:
        with database.get_db_session() as db_new:
            exchange_key = db_new.query(models.ExchangeKey).filter(
                models.ExchangeKey.user_id == user_id,
                models.ExchangeKey.exchange_name == exchange_name,
            ).first()
            if exchange_key:
                from crypto_utils import decrypt_key
                api_key = decrypt_key(exchange_key.api_key_encrypted)
                api_secret = decrypt_key(exchange_key.api_secret_encrypted)
            else:
                logger.error("[Bot %d] No API key found for user %d. Cannot start live trading.", bot_config_id, user_id)
                set_bot_active(bot_config_id, False)
                return None

    execution = ExecutionEngine(
        api_key=api_key,
        api_secret=api_secret,
        exchange_name=exchange_name,
        paper_trading=paper_trading,
    )

    if not paper_trading and not execution.is_live_ready():
        logger.error("[Bot %d] Exchange connection failed. Stopping bot.", bot_config_id)
        set_bot_active(bot_config_id, False)
        return None

    # Portfolio State — DB에서 복구 시도
    active_positions: dict = load_positions_from_db(bot_config_id)
    cooldown_until: dict[str, datetime] = {}

    for sym, pos in active_positions.items():
        invested: float = pos['entry_price'] * pos['position_amount']
        liquid_capital -= invested
        logger.info("[Bot %d] Recovered position %s: entry=%.0f, qty=%.4f", bot_config_id, sym, pos['entry_price'], pos['position_amount'])

    set_bot_active(bot_config_id, True)

    return {
        "symbols": symbols,
        "timeframe": cfg["timeframe"],
        "liquid_capital": liquid_capital,
        "paper_trading": paper_trading,
        "strategy_name": cfg["strategy_name"],
        "exchange_name": exchange_name,
        "user_id": user_id,
        "strategy": strategy,
        "execution": execution,
        "active_positions": active_positions,
        "cooldown_until": cooldown_until,
    }


async def run_bot_loop(bot_config_id: int) -> None:
    logger.info("--- [Bot %d] Engine Started (Portfolio Mode) ---", bot_config_id)

    init = _initialize_bot_engine(bot_config_id)
    if init is None:
        return

    fetcher_exchange_id = init.get("exchange_name", "upbit") or "upbit"
    fetcher = DataFetcher(exchange_id=fetcher_exchange_id)

    symbols: list[str] = init["symbols"]
    timeframe: str = init["timeframe"]
    liquid_capital: float = init["liquid_capital"]
    paper_trading: bool = init["paper_trading"]
    strategy_name: str = init["strategy_name"]
    user_id: int = init["user_id"]
    strategy = init["strategy"]
    execution: ExecutionEngine = init["execution"]
    active_positions: dict = init["active_positions"]
    cooldown_until: dict[str, datetime] = init["cooldown_until"]

    consecutive_errors: int = 0
    last_feedback_candle_close: int = -1  # 마지막으로 피드백을 보낸 캔들 마감 시각(분)

    # 봇 시작 알림
    mode_label = "모의투자" if paper_trading else "실매매"
    strategy_label = STRATEGY_LABELS.get(strategy_name, strategy_name)
    symbols_str = ", ".join(symbols)

    # 실매매: 업비트 실제 잔고 표시
    if not paper_trading:
        real_balance = execution.fetch_total_balance_krw()
        capital_line = f"💰 업비트 자산: {real_balance:,.0f} KRW" if real_balance is not None else f"자본: {liquid_capital:,.0f} KRW"
    else:
        capital_line = f"자본: {liquid_capital:,.0f} KRW"

    # 종목별 현재가 조회
    symbol_price_lines: list[str] = []
    for sym in symbols:
        try:
            ticker = fetcher.exchange.fetch_ticker(sym)
            price = ticker.get('last', 0)
            symbol_price_lines.append(f"  {sym}: {float(price):,.0f} KRW")
        except Exception:
            symbol_price_lines.append(f"  {sym}: 조회 실패")

    _send_bot_status_notification(user_id, (
        f"🟢 봇 시작\n"
        f"모드: {mode_label}\n"
        f"전략: {strategy_label}\n"
        f"타임프레임: {timeframe}\n"
        f"{capital_line}\n"
        f"{'─' * 24}\n"
        f"📊 종목 현재가\n"
        + "\n".join(symbol_price_lines)
    ))

    try:
        while True:
            logger.info("--- [Bot %d] Portfolio Tick: %d symbols ---", bot_config_id, len(symbols))

            # 1. Update Total Equity (Liquid + Current Positions Value)
            total_equity: float = liquid_capital
            current_prices: dict[str, float] = {}

            current_db = database.SessionLocal()
            try:
                signal_details: list[str] = []

                # First pass: Fetch data for all symbols and update equity
                for symbol in symbols:
                    # Use async wrapper to avoid blocking the event loop with time.sleep()
                    df = await fetcher.fetch_ohlcv_async(symbol=symbol, timeframe=timeframe, limit=300, db=current_db)
                    if df is None or df.empty:
                        continue

                    # 실시간 현재가: ticker API에서 가져옴 (DB 캐시 캔들은 업데이트 안 되므로)
                    try:
                        ticker = await asyncio.get_running_loop().run_in_executor(
                            None, lambda s=symbol: fetcher.exchange.fetch_ticker(s)
                        )
                        curr_price: float = float(ticker.get('last', 0))
                    except Exception:
                        curr_price = float(df.iloc[-1]['close'])  # fallback
                    current_prices[symbol] = curr_price
                    if symbol in active_positions:
                        total_equity += (active_positions[symbol]['position_amount'] * curr_price)

                    # Process logic for this symbol
                    df = strategy.apply_indicators(df)
                    # Use iloc[-2] (last CLOSED candle) for all signal checks.
                    # iloc[-1] is the still-forming candle and must not be used for signals.
                    current_idx: int = len(df) - 2

                    # Guard: need at least 2 candles for current_idx >= 0, and strategies
                    # need current_idx >= 1 to access prev candle
                    if current_idx < 1:
                        continue

                    # 신호 분석 (텔레그램 피드백용)
                    has_buy_signal = strategy.check_buy_signal(df, current_idx)
                    current_data = df.iloc[current_idx]
                    rsi_col = getattr(strategy, 'rsi_col', 'RSI_14')
                    macd_col = getattr(strategy, 'macd_col', 'MACD_12_26_9')
                    macds_col = getattr(strategy, 'macds_col', 'MACDs_12_26_9')
                    rsi_val = current_data.get(rsi_col, None)
                    macd_val = current_data.get(macd_col, None)
                    macds_val = current_data.get(macds_col, None)
                    atr_col = getattr(strategy, 'atr_col', 'ATR_14')
                    atr_val = current_data.get(atr_col, None)
                    vol_ma_col = getattr(strategy, 'vol_ma_col', 'VOL_SMA_20')
                    vol_ma_val = current_data.get(vol_ma_col, 0)
                    vol_ratio = (current_data['volume'] / vol_ma_val) if vol_ma_val and not pd.isna(vol_ma_val) and vol_ma_val > 0 else 0

                    if symbol in active_positions:
                        pos = active_positions[symbol]

                        # A. Exit Check
                        liquid_capital, was_exited = _process_symbol_exit(
                            symbol, pos, curr_price, execution,
                            bot_config_id, user_id, liquid_capital,
                            paper_trading=paper_trading,
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
                                if atr_val is not None and not pd.isna(atr_val) and atr_val > 0:
                                    new_sl = strategy.update_trailing_stop(curr_price, atr_val, pos['stop_loss'])
                                    if new_sl > pos['stop_loss']:
                                        pos['stop_loss'] = new_sl

                            # 보유 중 상태 피드백
                            pnl_pct = ((curr_price - pos['entry_price']) / pos['entry_price'] * 100) if pos['entry_price'] > 0 else 0
                            sl_dist = ((curr_price - pos['stop_loss']) / curr_price * 100) if curr_price > 0 else 0
                            tp_dist = ((pos['take_profit'] - curr_price) / curr_price * 100) if curr_price > 0 else 0
                            pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"
                            rsi_str = f"{rsi_val:.1f}" if rsi_val is not None and not pd.isna(rsi_val) else "N/A"
                            macd_str = "상승" if (macd_val is not None and macds_val is not None and not pd.isna(macd_val) and not pd.isna(macds_val) and macd_val > macds_val) else "하락"
                            vol_str = f"{vol_ratio:.1f}x" if vol_ratio and not pd.isna(vol_ratio) else "N/A"
                            signal_details.append(
                                f"📊 {symbol}\n"
                                f"  보유중 | 현재가: {curr_price:,.0f}\n"
                                f"  {pnl_emoji} 손익: {pnl_pct:+.2f}% | SL까지: {sl_dist:.1f}% | TP까지: {tp_dist:.1f}%\n"
                                f"  RSI: {rsi_str} | MACD: {macd_str} | 거래량: {vol_str}"
                            )
                    else:
                        # C. Entry Check (포지션 수 제한 + 쿨다운 체크)
                        entry_skipped_reason = None
                        if len(active_positions) >= MAX_CONCURRENT_POSITIONS:
                            entry_skipped_reason = "최대 포지션 도달"
                        elif symbol in cooldown_until and datetime.now() < cooldown_until[symbol]:
                            entry_skipped_reason = "손절 쿨다운 중"
                        else:
                            liquid_capital, new_position = _process_symbol_entry(
                                symbol, df, curr_price, current_idx, strategy,
                                execution, bot_config_id, user_id,
                                total_equity, liquid_capital,
                            )
                            if new_position:
                                active_positions[symbol] = new_position
                                cooldown_until.pop(symbol, None)

                        # 미보유 상태 피드백
                        status_str = "⚡매수 신호!" if has_buy_signal else "대기중"
                        if entry_skipped_reason and has_buy_signal:
                            status_str = f"⚡신호 있으나 {entry_skipped_reason}"
                        rsi_str = f"{rsi_val:.1f}" if rsi_val is not None and not pd.isna(rsi_val) else "N/A"
                        macd_str = "상승" if (macd_val is not None and macds_val is not None and not pd.isna(macd_val) and not pd.isna(macds_val) and macd_val > macds_val) else "하락"
                        vol_str = f"{vol_ratio:.1f}x" if vol_ratio and not pd.isna(vol_ratio) else "N/A"
                        signal_details.append(
                            f"{'🟢' if has_buy_signal else '⚪'} {symbol}\n"
                            f"  {status_str} | 현재가: {curr_price:,.0f}\n"
                            f"  RSI: {rsi_str} | MACD: {macd_str} | 거래량: {vol_str}"
                        )

                # 매 tick마다 포지션 상태를 DB에 저장
                save_positions_to_db(bot_config_id, active_positions)

                logger.info(
                    "[Bot %d] Status: Equity=%s | Liquid=%s | Positions=%s",
                    bot_config_id,
                    f"{total_equity:,.0f}",
                    f"{liquid_capital:,.0f}",
                    list(active_positions.keys()),
                )

                # 캔들 마감 시점에 1회만 피드백 전송 (가장 가까운 마감 시각 기준 중복 방지)
                nearest_close = _get_nearest_candle_close(timeframe)
                if (signal_details
                        and _is_candle_close_time(timeframe)
                        and nearest_close != last_feedback_candle_close):
                    last_feedback_candle_close = nearest_close

                    # 실매매 모드: 업비트 실제 잔고 조회
                    real_balance_krw: float | None = None
                    if not paper_trading:
                        real_balance_krw = execution.fetch_total_balance_krw()

                    feedback_msg = _build_tick_feedback(
                        signal_details, paper_trading, strategy_name, timeframe, total_equity,
                        real_balance_krw=real_balance_krw,
                    )
                    _send_trade_notification(user_id, feedback_msg)

                consecutive_errors = 0  # 성공 시 에러 카운터 초기화

            except Exception as e:
                consecutive_errors += 1
                logger.error("[Bot %d] Loop error (%d/%d): %s", bot_config_id, consecutive_errors, MAX_CONSECUTIVE_ERRORS, e)
                logger.debug(traceback.format_exc())
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error("[Bot %d] Too many consecutive errors. Stopping bot.", bot_config_id)
                    # 에러로 중단해도 포지션은 DB에 저장
                    save_positions_to_db(bot_config_id, active_positions)
                    _send_bot_status_notification(user_id, f"🔴 봇 자동 종료\n전략: {strategy_label}\n사유: 연속 오류 {MAX_CONSECUTIVE_ERRORS}회")
                    break
            finally:
                current_db.close()

            # 에러가 연속되면 대기 시간을 늘림 (최대 5분)
            sleep_time: int = min(60 * (1 + consecutive_errors), 300)
            await asyncio.sleep(sleep_time)
    except asyncio.CancelledError:
        logger.info("--- [Bot %d] Engine Stopped (graceful) ---", bot_config_id)
        # 포지션은 DB에 유지 (재시작 시 복구 가능)
        save_positions_to_db(bot_config_id, active_positions)
        _send_bot_status_notification(user_id, f"🔴 봇 종료\n전략: {strategy_label}\n종목: {symbols_str}")
        raise
    except Exception as e:
        logger.error("[Bot %d] Fatal error in bot loop: %s", bot_config_id, e)
        logger.debug(traceback.format_exc())
        _send_bot_status_notification(user_id, f"🔴 봇 비정상 종료\n전략: {strategy_label}\n오류: {str(e)[:100]}")
    finally:
        # Clean up from active_bots so status correctly reports Stopped
        active_bots.pop(bot_config_id, None)
        # 서버 셧다운 중이면 is_active=True를 유지하여 재시작 시 자동 복구 가능
        if not _shutting_down:
            set_bot_active(bot_config_id, False)


def get_bot_status(bot_config_id: int) -> str:
    task = active_bots.get(bot_config_id)
    if task is not None and not task.done():
        return "Running"
    return "Stopped"


# ──────────────────────────────────────────────
# 서버 시작 시 봇 자동 복구 & Graceful Shutdown
# ──────────────────────────────────────────────

async def recover_active_bots() -> None:
    """서버 시작 시 DB에서 is_active=True인 봇을 자동 재가동"""
    with database.get_db_session() as db:
        try:
            active_bot_configs = db.query(models.BotConfig).filter(
                models.BotConfig.is_active == True,
            ).all()

            if not active_bot_configs:
                logger.info("[Recovery] No active bots to recover.")
                return

            for bot_cfg in active_bot_configs:
                bot_id: int = bot_cfg.id
                paper_label: str = "모의투자" if bot_cfg.paper_trading_mode else "실매매"
                logger.info(
                    "[Recovery] Restarting bot %d (%s, %s, %s)",
                    bot_id, bot_cfg.symbol, bot_cfg.strategy_name, paper_label,
                )
                task = asyncio.create_task(run_bot_loop(bot_id))
                active_bots[bot_id] = task

            logger.info("[Recovery] Recovered %d bot(s).", len(active_bot_configs))
        except Exception as e:
            logger.error("[Recovery] Failed to recover bots: %s", e)


async def graceful_shutdown() -> None:
    """서버 종료 시 모든 봇을 안전하게 중단 (포지션은 DB에 유지, is_active=True 보존)"""
    global _shutting_down

    if not active_bots:
        return

    logger.info("[Shutdown] Stopping %d active bot(s)...", len(active_bots))

    # 셧다운 플래그 설정 → finally 블록에서 is_active=False 설정을 건너뜀
    _shutting_down = True

    tasks = list(active_bots.values())
    for task in tasks:
        task.cancel()

    # 모든 태스크가 종료될 때까지 대기 (최대 10초)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.error("[Shutdown] Bot task error: %s", result)

    logger.info("[Shutdown] All bots stopped. Positions preserved in DB.")
