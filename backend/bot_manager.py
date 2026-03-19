import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Optional

import pandas as pd

import database
import models
from constants import (
    EXCHANGE_LABELS,
    MAX_CONCURRENT_POSITIONS,
    MAX_CONSECUTIVE_ERRORS,
    STOP_LOSS_COOLDOWN_SECONDS,
    STRATEGY_LABELS,
)
from core.data_fetcher import DataFetcher
from core.execution import ExecutionEngine
from notifications import send_trade_notification, send_bot_status_notification

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
            "custom_strategy_id": getattr(bot_config, 'custom_strategy_id', None),
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

    cost_basis: float = pos['entry_price'] * pos['position_amount']
    pnl_pct: float = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    reason_kr = {"Stop Loss": "🛑 손절", "Take Profit": "🎯 익절"}.get(reason, reason)
    trade_mode = "모의" if paper_trading else "실매매"
    msg = (
        f"📉 매도 체결 [{trade_mode}]\n"
        f"{'─' * 24}\n"
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

    # 백테스트와 동일: 고정 비율 SL/TP 사용 (backtest_sl_pct / backtest_tp_pct)
    sl_pct = getattr(strategy, 'backtest_sl_pct', 0.015)
    tp_pct = getattr(strategy, 'backtest_tp_pct', 0.03)
    sl = curr_price * (1 - sl_pct) if sl_pct is not None else curr_price * 0.9
    tp = curr_price * (1 + tp_pct) if tp_pct is not None else curr_price * 1.5

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

    sl_pct = abs((sl - entry_price) / entry_price * 100) if entry_price > 0 else 0
    tp_pct = abs((tp - entry_price) / entry_price * 100) if entry_price > 0 else 0
    msg = (
        f"📈 매수 체결\n"
        f"{'─' * 24}\n"
        f"종목: {symbol}\n"
        f"체결가: {entry_price:,.0f} KRW\n"
        f"수량: {qty:.4f}\n"
        f"🛑 손절: {sl:,.0f} (-{sl_pct:.1f}%)\n"
        f"🎯 익절: {tp:,.0f} (+{tp_pct:.1f}%)"
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


# 사용자별 알림 주기 설정 → 분 단위 매핑
_NOTIFICATION_INTERVAL_MINUTES: dict[str, int] = {
    'realtime': 0,    # 매 캔들 마감마다
    '4h': 240,
    '12h': 720,
    'daily': 1440,
}


def _get_user_notification_interval(user_id: int) -> str:
    """DB에서 사용자의 notification_interval 설정을 조회."""
    try:
        with database.get_db_session() as db:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user and user.notification_interval:
                return user.notification_interval
    except Exception as e:
        logger.error("[Notification] Failed to get interval for user %d: %s", user_id, e)
    return "realtime"


def _should_send_feedback(user_id: int, timeframe: str, last_feedback_ts: float) -> bool:
    """사용자의 알림 주기 설정에 따라 정기 피드백을 전송할지 결정.
    - realtime: 매 캔들 마감마다 (기존 동작)
    - 4h/12h/daily: 해당 간격 이상 경과한 경우에만 전송
    """
    interval_setting = _get_user_notification_interval(user_id)

    if interval_setting == "realtime":
        return True  # 매 캔들 마감마다 전송

    interval_minutes = _NOTIFICATION_INTERVAL_MINUTES.get(interval_setting, 0)
    if interval_minutes <= 0:
        return True

    # 마지막 피드백 이후 경과 시간(분) 확인
    now_ts = datetime.now().timestamp()
    elapsed_minutes = (now_ts - last_feedback_ts) / 60

    return elapsed_minutes >= interval_minutes


def _build_tick_feedback(
    signal_details: list[str],
    paper_trading: bool,
    strategy_name: str,
    timeframe: str,
    total_equity: float,
    exchange_name: str = "upbit",
) -> str:
    """매 tick 텔레그램 정기 피드백 메시지 생성."""
    mode_label = "🧪 모의투자" if paper_trading else "💵 실매매"
    now_str = datetime.now().strftime("%m/%d %H:%M")
    strategy_label = STRATEGY_LABELS.get(strategy_name, strategy_name)
    exchange_label = EXCHANGE_LABELS.get(exchange_name, exchange_name)

    asset_line = f"💰 봇 자산: {total_equity:,.0f} KRW"

    return (
        f"{mode_label} · {strategy_label}\n"
        f"⏰ {now_str} | {timeframe}봉 분석 완료\n"
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

    from core.strategy import get_strategy, get_strategy_with_custom_params

    # 커스텀 전략이면 파라미터 적용
    custom_strategy_id = cfg.get("custom_strategy_id")
    if custom_strategy_id:
        import json
        with database.get_db_session() as db_strat:
            user_strat = db_strat.query(models.UserStrategy).filter(
                models.UserStrategy.id == custom_strategy_id,
                models.UserStrategy.is_deleted == False,
            ).first()
            if user_strat:
                custom_params = json.loads(user_strat.custom_params) if user_strat.custom_params else {}
                strategy = get_strategy_with_custom_params(user_strat.base_strategy_name, custom_params)
                logger.info("[Bot %d] Using custom strategy '%s' (base: %s)", bot_config_id, user_strat.name, user_strat.base_strategy_name)
            else:
                strategy = get_strategy(cfg["strategy_name"])
                logger.warning("[Bot %d] Custom strategy %d not found, using default", bot_config_id, custom_strategy_id)
    else:
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


async def run_bot_loop(bot_config_id: int, *, is_recovery: bool = False) -> None:
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
    last_feedback_ts: float = 0.0  # 마지막 피드백 전송 unix timestamp
    first_tick_after_recovery: bool = is_recovery  # 복구 후 첫 tick에서 즉시 분석 전송

    # 봇 시작 알림
    mode_label = "🧪 모의투자" if paper_trading else "💵 실매매"
    strategy_label = STRATEGY_LABELS.get(strategy_name, strategy_name)
    exchange_name: str = init.get("exchange_name", "upbit") or "upbit"
    exchange_label = EXCHANGE_LABELS.get(exchange_name, exchange_name)
    symbols_str = ", ".join(symbols)

    capital_line = f"💰 투입 자본: {liquid_capital:,.0f} KRW"

    # 종목별 현재가 조회
    symbol_price_lines: list[str] = []
    for sym in symbols:
        try:
            ticker = fetcher.exchange.fetch_ticker(sym)
            price = ticker.get('last', 0)
            symbol_price_lines.append(f"  {sym}: {float(price):,.0f} KRW")
        except Exception:
            symbol_price_lines.append(f"  {sym}: 조회 실패")

    if is_recovery:
        # 서버 재시작 복구: 알림 전송 + 첫 tick에서 즉시 분석 결과 전송
        pos_lines: list[str] = []
        for sym, pos in active_positions.items():
            pos_lines.append(f"  {sym}: 진입가 {pos['entry_price']:,.0f}")
        pos_section = ""
        if pos_lines:
            pos_section = f"\n📦 보유 포지션 복구\n" + "\n".join(pos_lines)
        _send_bot_status_notification(user_id, (
            f"🔄 봇 자동 복구 완료\n"
            f"{'─' * 24}\n"
            f"모드: {mode_label}\n"
            f"전략: {strategy_label}\n"
            f"타임프레임: {timeframe}봉\n"
            f"거래소: {exchange_label}\n"
            f"{capital_line}"
            f"{pos_section}\n"
            f"{'─' * 24}\n"
            f"📊 종목 현재가\n"
            + "\n".join(symbol_price_lines)
        ))
    else:
        _send_bot_status_notification(user_id, (
            f"🟢 봇 가동 시작\n"
            f"{'─' * 24}\n"
            f"모드: {mode_label}\n"
            f"전략: {strategy_label}\n"
            f"타임프레임: {timeframe}봉\n"
            f"거래소: {exchange_label}\n"
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
                    # timestamp 컬럼이 Timestamp 타입이면 indicator 값 비교 시
                    # 'float > Timestamp' 에러 발생 → index로 이동하여 제거
                    if 'timestamp' in df.columns:
                        df = df.set_index('timestamp', drop=True)
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
                    adx_col = getattr(strategy, 'adx_col', 'ADX_14')
                    adx_val = current_data.get(adx_col, None)
                    dmp_col = getattr(strategy, 'dmp_col', 'DMP_14')
                    dmn_col = getattr(strategy, 'dmn_col', 'DMN_14')
                    dmp_val = current_data.get(dmp_col, None)
                    dmn_val = current_data.get(dmn_col, None)
                    vol_ma_col = getattr(strategy, 'vol_ma_col', 'VOL_SMA_20')
                    vol_ma_val = current_data.get(vol_ma_col, 0)
                    vol_ratio = (current_data['volume'] / vol_ma_val) if vol_ma_val and not pd.isna(vol_ma_val) and vol_ma_val > 0 else 0
                    ema_200 = current_data.get('EMA_200', None)
                    ema_50 = current_data.get('EMA_50', None)

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
                            # 백테스트와 동일: 트레일링 스탑 미사용 (고정 SL/TP)

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

                        # 미보유 상태 피드백 (진입 조건 상세 포함)
                        status_str = "⚡매수 신호!" if has_buy_signal else "대기중"
                        if entry_skipped_reason and has_buy_signal:
                            status_str = f"⚡신호 있으나 {entry_skipped_reason}"
                        rsi_str = f"{rsi_val:.1f}" if rsi_val is not None and not pd.isna(rsi_val) else "N/A"
                        macd_str = "상승" if (macd_val is not None and macds_val is not None and not pd.isna(macd_val) and not pd.isna(macds_val) and macd_val > macds_val) else "하락"
                        vol_str = f"{vol_ratio:.1f}x" if vol_ratio and not pd.isna(vol_ratio) else "N/A"
                        adx_str = f"{adx_val:.1f}" if adx_val is not None and not pd.isna(adx_val) else "N/A"

                        # 진입 조건 충족 여부 체크리스트 (전략별 실제 필터 기반)
                        conditions: list[str] = []
                        for label, is_met in strategy.get_entry_conditions(df, current_idx, curr_price):
                            conditions.append(f"  {'✅' if is_met else '❌'} {label}")

                        conditions_str = "\n".join(conditions)
                        signal_details.append(
                            f"{'🟢' if has_buy_signal else '⚪'} {symbol}\n"
                            f"  {status_str} | 현재가: {curr_price:,.0f}\n"
                            f"{conditions_str}"
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

                # 캔들 마감 시점에 피드백 전송 (사용자 알림 주기 설정 반영)
                # 복구 후 첫 tick에서는 캔들 마감 체크 없이 즉시 전송
                nearest_close = _get_nearest_candle_close(timeframe)
                should_send_now = first_tick_after_recovery and signal_details
                should_send_scheduled = (
                    signal_details
                    and _is_candle_close_time(timeframe)
                    and nearest_close != last_feedback_candle_close
                    and _should_send_feedback(user_id, timeframe, last_feedback_ts)
                )
                if should_send_now or should_send_scheduled:
                    last_feedback_candle_close = nearest_close
                    last_feedback_ts = datetime.now().timestamp()
                    first_tick_after_recovery = False

                    feedback_msg = _build_tick_feedback(
                        signal_details, paper_trading, strategy_name, timeframe, total_equity,
                        exchange_name=exchange_name,
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
                    _send_bot_status_notification(user_id, f"🔴 봇 자동 종료\n{'─' * 24}\n전략: {strategy_label} · {timeframe}봉\n사유: 연속 오류 {MAX_CONSECUTIVE_ERRORS}회 발생\n포지션은 DB에 보존됩니다.")
                    break
            finally:
                current_db.close()

            # 에러가 연속되면 대기 시간을 늘림 (최대 5분)
            sleep_time: int = min(60 * (1 + consecutive_errors), 300)
            await asyncio.sleep(sleep_time)
    except asyncio.CancelledError:
        logger.info("--- [Bot %d] Engine Stopped (graceful) ---", bot_config_id)

        if _shutting_down:
            # 서버 셧다운: 포지션 DB 보존 (재시작 시 자동 복구)
            save_positions_to_db(bot_config_id, active_positions)
        else:
            # 사용자 수동 종료: 보유 포지션 전량 시장가 매도
            closed_details: list[str] = []
            for sym, pos in list(active_positions.items()):
                try:
                    curr_price = float(fetcher.exchange.fetch_ticker(sym).get('last', 0))
                except Exception:
                    curr_price = pos['entry_price']  # fallback

                sell_result = execution.execute_sell(
                    sym, curr_price, pos['position_amount'], reason="Bot Stop",
                )
                if sell_result and sell_result["status"] == "success":
                    actual_price = sell_result.get("price", curr_price)
                    actual_amount = sell_result.get("amount", pos['position_amount'])
                    pnl = (actual_price - pos['entry_price']) * actual_amount
                    save_trade_log(bot_config_id, sym, "SELL", actual_price, actual_amount, "Bot Stop (청산)", pnl)
                    pnl_pct = (pnl / (pos['entry_price'] * pos['position_amount']) * 100) if pos['entry_price'] > 0 else 0
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    closed_details.append(f"  {sym}: {actual_price:,.0f} KRW ({pnl_emoji}{pnl_pct:+.2f}%)")
                    logger.info("[Bot %d] Stop-close %s: price=%.0f, pnl=%.0f", bot_config_id, sym, actual_price, pnl)
                else:
                    closed_details.append(f"  {sym}: ❌ 매도 실패 — 거래소에서 직접 확인 필요")
                    logger.error("[Bot %d] Failed to close position %s on stop", bot_config_id, sym)

            active_positions.clear()
            save_positions_to_db(bot_config_id, active_positions)

            # 종료 알림 (청산 내역 포함)
            close_section = ""
            if closed_details:
                close_section = f"\n📉 포지션 청산\n" + "\n".join(closed_details)
            _send_bot_status_notification(user_id, (
                f"🔴 봇 정상 종료\n"
                f"{'─' * 24}\n"
                f"전략: {strategy_label} · {timeframe}봉\n"
                f"종목: {symbols_str}"
                f"{close_section}"
            ))
        raise
    except Exception as e:
        logger.error("[Bot %d] Fatal error in bot loop: %s", bot_config_id, e)
        logger.debug(traceback.format_exc())
        _send_bot_status_notification(user_id, f"🔴 봇 비정상 종료\n{'─' * 24}\n전략: {strategy_label} · {timeframe}봉\n오류: {str(e)[:100]}\n포지션은 DB에 보존됩니다.")
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
                task = asyncio.create_task(run_bot_loop(bot_id, is_recovery=True))
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
