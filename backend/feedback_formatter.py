"""
feedback_formatter.py — 텔레그램 알림 메시지 포맷팅

bot_manager.py에서 분리된 알림 메시지 생성 로직.
비즈니스 로직 없이 순수 포맷팅만 담당.
"""

from datetime import datetime

from constants import EXCHANGE_LABELS, STRATEGY_LABELS

SEPARATOR = "─" * 24


def format_sell_notification(
    symbol: str,
    actual_price: float,
    pnl_pct: float,
    pnl: float,
    reason: str,
    paper_trading: bool,
) -> str:
    """매도 체결 알림 메시지."""
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    reason_kr = {"Stop Loss": "🛑 손절", "Take Profit": "🎯 익절"}.get(reason, reason)
    trade_mode = "모의" if paper_trading else "실매매"
    return (
        f"📉 매도 체결 [{trade_mode}]\n"
        f"{SEPARATOR}\n"
        f"종목: {symbol}\n"
        f"체결가: {actual_price:,.0f} KRW\n"
        f"{pnl_emoji} 손익: {pnl_pct:+.2f}% ({pnl:+,.0f} KRW)\n"
        f"사유: {reason_kr}"
    )


def format_buy_notification(
    symbol: str,
    entry_price: float,
    qty: float,
    sl: float,
    tp: float,
) -> str:
    """매수 체결 알림 메시지."""
    sl_pct = abs((sl - entry_price) / entry_price * 100) if entry_price > 0 else 0
    tp_pct = abs((tp - entry_price) / entry_price * 100) if entry_price > 0 else 0
    return (
        f"📈 매수 체결\n"
        f"{SEPARATOR}\n"
        f"종목: {symbol}\n"
        f"체결가: {entry_price:,.0f} KRW\n"
        f"수량: {qty:.4f}\n"
        f"🛑 손절: {sl:,.0f} (-{sl_pct:.1f}%)\n"
        f"🎯 익절: {tp:,.0f} (+{tp_pct:.1f}%)"
    )


def format_tick_feedback(
    signal_details: list[str],
    paper_trading: bool,
    strategy_name: str,
    timeframe: str,
    total_equity: float,
    exchange_name: str = "upbit",
) -> str:
    """매 tick 텔레그램 정기 피드백 메시지."""
    mode_label = "🧪 모의투자" if paper_trading else "💵 실매매"
    now_str = datetime.now().strftime("%m/%d %H:%M")
    strategy_label = STRATEGY_LABELS.get(strategy_name, strategy_name)
    asset_line = f"💰 봇 자산: {total_equity:,.0f} KRW"

    return (
        f"{mode_label} · {strategy_label}\n"
        f"⏰ {now_str} | {timeframe}봉 분석 완료\n"
        f"{asset_line}\n"
        f"{SEPARATOR}\n"
        + f"\n{SEPARATOR}\n".join(signal_details)
    )


def format_bot_start_notification(
    paper_trading: bool,
    strategy_name: str,
    timeframe: str,
    exchange_name: str,
    liquid_capital: float,
    symbol_price_lines: list[str],
    is_recovery: bool = False,
    position_lines: list[str] | None = None,
) -> str:
    """봇 가동/복구 알림 메시지."""
    mode_label = "🧪 모의투자" if paper_trading else "💵 실매매"
    strategy_label = STRATEGY_LABELS.get(strategy_name, strategy_name)
    exchange_label = EXCHANGE_LABELS.get(exchange_name, exchange_name)
    capital_line = f"💰 투입 자본: {liquid_capital:,.0f} KRW"

    if is_recovery:
        pos_section = ""
        if position_lines:
            pos_section = f"\n📦 보유 포지션 복구\n" + "\n".join(position_lines)
        return (
            f"🔄 봇 자동 복구 완료\n"
            f"{SEPARATOR}\n"
            f"모드: {mode_label}\n"
            f"전략: {strategy_label}\n"
            f"타임프레임: {timeframe}봉\n"
            f"거래소: {exchange_label}\n"
            f"{capital_line}"
            f"{pos_section}\n"
            f"{SEPARATOR}\n"
            f"📊 종목 현재가\n"
            + "\n".join(symbol_price_lines)
        )
    else:
        return (
            f"🟢 봇 가동 시작\n"
            f"{SEPARATOR}\n"
            f"모드: {mode_label}\n"
            f"전략: {strategy_label}\n"
            f"타임프레임: {timeframe}봉\n"
            f"거래소: {exchange_label}\n"
            f"{capital_line}\n"
            f"{SEPARATOR}\n"
            f"📊 종목 현재가\n"
            + "\n".join(symbol_price_lines)
        )


def format_bot_stop_notification(
    strategy_label: str,
    timeframe: str,
    symbols_str: str,
    closed_details: list[str] | None = None,
) -> str:
    """봇 정상 종료 알림 메시지."""
    close_section = ""
    if closed_details:
        close_section = f"\n📉 포지션 청산\n" + "\n".join(closed_details)
    return (
        f"🔴 봇 정상 종료\n"
        f"{SEPARATOR}\n"
        f"전략: {strategy_label} · {timeframe}봉\n"
        f"종목: {symbols_str}"
        f"{close_section}"
    )


def format_bot_error_stop(
    strategy_label: str,
    timeframe: str,
    max_errors: int,
) -> str:
    """연속 에러로 인한 봇 중단 알림."""
    return (
        f"🔴 봇 자동 종료\n"
        f"{SEPARATOR}\n"
        f"전략: {strategy_label} · {timeframe}봉\n"
        f"사유: 연속 오류 {max_errors}회 발생\n"
        f"포지션은 DB에 보존됩니다."
    )


def format_bot_fatal_error(
    strategy_label: str,
    timeframe: str,
    error_msg: str,
) -> str:
    """봇 비정상 종료 알림."""
    return (
        f"🔴 봇 비정상 종료\n"
        f"{SEPARATOR}\n"
        f"전략: {strategy_label} · {timeframe}봉\n"
        f"오류: {error_msg[:100]}\n"
        f"포지션은 DB에 보존됩니다."
    )


def format_holding_signal(
    symbol: str,
    curr_price: float,
    entry_price: float,
    pnl_pct: float,
    pnl_abs: float,
    stop_loss: float,
    take_profit: float | None,
    sl_dist: float,
    tp_dist: float | None,
    rsi_val: float | None,
    prev_rsi_val: float | None,
    macd_rising: bool,
    vol_ratio: float,
) -> str:
    """보유 중 종목 신호 상세 (SL/TP 절대가 + 청산 압박 지표 포함)."""
    pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"

    # SL/TP 라인
    sl_line = f"  🛑 SL: {stop_loss:,.0f} (남은 -{sl_dist:.1f}%)"
    if take_profit is not None and tp_dist is not None:
        tp_line = f"  🎯 TP: {take_profit:,.0f} (남은 +{tp_dist:.1f}%)"
    else:
        tp_line = "  🎯 TP: 트레일링 (제한 없음)"

    # 청산 압박 지표
    pressure_lines: list[str] = []

    # RSI
    if rsi_val is not None:
        if rsi_val > 75:
            rsi_note = "⚠️ 극과매수"
        elif rsi_val > 70:
            rsi_note = "⚠️ 과매수 구간"
            if prev_rsi_val is not None and rsi_val < prev_rsi_val:
                rsi_note += " + 하락 전환"
        else:
            rsi_note = "✅ 정상"
        pressure_lines.append(f"  RSI {rsi_val:.1f}: {rsi_note}")
    else:
        pressure_lines.append("  RSI: N/A")

    # MACD
    if macd_rising:
        pressure_lines.append("  MACD: 상승 중 ✅")
    else:
        pressure_lines.append("  MACD: ⚠️ 하락 전환")

    # 거래량
    if vol_ratio > 0:
        if vol_ratio < 0.5:
            vol_note = f"⚠️ 급감 ({vol_ratio:.1f}x)"
        elif vol_ratio >= 1.5:
            vol_note = f"🔥 급증 ({vol_ratio:.1f}x)"
        else:
            vol_note = f"✅ 보통 ({vol_ratio:.1f}x)"
        pressure_lines.append(f"  거래량: {vol_note}")

    pressure_str = "\n".join(pressure_lines)

    return (
        f"📦 {symbol}\n"
        f"  보유중 | 현재가: {curr_price:,.0f} | 진입가: {entry_price:,.0f}\n"
        f"  {pnl_emoji} 손익: {pnl_pct:+.2f}% ({pnl_abs:+,.0f} KRW)\n"
        f"{sl_line}\n"
        f"{tp_line}\n"
        f"  ── 청산 압박 ──\n"
        f"{pressure_str}"
    )


def format_waiting_signal(
    symbol: str,
    curr_price: float,
    has_buy_signal: bool,
    entry_skipped_reason: str | None,
    conditions: list[str],
) -> str:
    """미보유 종목 신호 상세."""
    status_str = "⚡매수 신호!" if has_buy_signal else "대기중"
    if entry_skipped_reason and has_buy_signal:
        status_str = f"⚡신호 있으나 {entry_skipped_reason}"
    icon = "🟢" if has_buy_signal else "⚪"
    conditions_str = "\n".join(conditions)
    return (
        f"{icon} {symbol}\n"
        f"  {status_str} | 현재가: {curr_price:,.0f}\n"
        f"{conditions_str}"
    )
