"""
OKX 선물 거래소 클라이언트 — CCXT 기반
"""
import ccxt
import pandas as pd
import logging

from settings import settings

logger = logging.getLogger("okx_futures")


def create_okx_client(credentials: dict | None = None) -> ccxt.okx:
    """OKX 선물 클라이언트 생성 (USDT-M Swap)

    Args:
        credentials: {"api_key", "secret_key", "passphrase"} — DB에서 로드된 키.
                      None이면 settings(.env)에서 로드.
    """
    if credentials:
        api_key = credentials["api_key"]
        secret = credentials["secret_key"]
        passphrase = credentials["passphrase"]
    else:
        api_key = settings.okx_api_key
        secret = settings.okx_secret_key
        passphrase = settings.okx_passphrase

    exchange = ccxt.okx({
        "apiKey": api_key,
        "secret": secret,
        "password": passphrase,  # OKX는 password 필드에 passphrase
        "options": {
            "defaultType": "swap",       # 무기한 선물
        },
    })
    exchange.set_sandbox_mode(False)
    return exchange


def fetch_ohlcv(
    exchange: ccxt.okx,
    symbol: str = "BTC/USDT:USDT",
    timeframe: str = "1h",
    limit: int = 300,
) -> pd.DataFrame:
    """OHLCV 데이터 조회 → DataFrame 변환"""
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def get_balance(exchange: ccxt.okx) -> dict:
    """USDT 잔고 조회"""
    balance = exchange.fetch_balance(params={"type": "swap"})
    usdt = balance.get("USDT", {})
    return {
        "total": float(usdt.get("total", 0)),
        "free": float(usdt.get("free", 0)),
        "used": float(usdt.get("used", 0)),
    }


def get_position(exchange: ccxt.okx, symbol: str = "BTC/USDT:USDT") -> dict | None:
    """현재 열린 포지션 조회"""
    positions = exchange.fetch_positions([symbol])
    for pos in positions:
        size = float(pos.get("contracts", 0) or 0)
        if size > 0:
            return {
                "side": pos["side"],           # "long" / "short"
                "size": size,
                "entry_price": float(pos["entryPrice"] or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
                "leverage": int(pos.get("leverage", 1) or 1),
                "liquidation_price": float(pos.get("liquidationPrice", 0) or 0),
            }
    return None


def set_leverage(
    exchange: ccxt.okx,
    symbol: str = "BTC/USDT:USDT",
    leverage: int = 3,
):
    """레버리지 설정"""
    try:
        exchange.set_leverage(leverage, symbol, params={"mgnMode": "isolated", "posSide": "net"})
        logger.info(f"레버리지 {leverage}x 설정 완료: {symbol}")
    except Exception as e:
        logger.warning(f"레버리지 설정 실패 (이미 설정됐을 수 있음): {e}")


def place_market_order(
    exchange: ccxt.okx,
    symbol: str,
    side: str,             # "buy" or "sell"
    amount: float,         # 계약 수
    reduce_only: bool = False,
) -> dict:
    """시장가 주문"""
    params = {"tdMode": "isolated"}
    if reduce_only:
        params["reduceOnly"] = True
    order = exchange.create_order(
        symbol=symbol,
        type="market",
        side=side,
        amount=amount,
        params=params,
    )
    logger.info(f"주문 체결: {side} {amount} {symbol} @ market")
    return order


def place_sl_tp_orders(
    exchange: ccxt.okx,
    symbol: str,
    side: str,              # 포지션 방향 "long" / "short"
    amount: float,
    stop_loss: float,
    take_profit: float,
):
    """SL/TP 주문 설정 (OKX algo order)"""
    close_side = "sell" if side == "long" else "buy"

    # Stop Loss
    try:
        exchange.create_order(
            symbol=symbol,
            type="stop",
            side=close_side,
            amount=amount,
            price=stop_loss,
            params={
                "tdMode": "isolated",
                "reduceOnly": True,
                "triggerPrice": stop_loss,
                "orderType": "market",
            },
        )
        logger.info(f"SL 설정: {stop_loss:.2f}")
    except Exception as e:
        logger.error(f"SL 주문 실패: {e}")

    # Take Profit
    try:
        exchange.create_order(
            symbol=symbol,
            type="stop",
            side=close_side,
            amount=amount,
            price=take_profit,
            params={
                "tdMode": "isolated",
                "reduceOnly": True,
                "triggerPrice": take_profit,
                "orderType": "market",
            },
        )
        logger.info(f"TP 설정: {take_profit:.2f}")
    except Exception as e:
        logger.error(f"TP 주문 실패: {e}")


def cancel_all_orders(exchange: ccxt.okx, symbol: str = "BTC/USDT:USDT"):
    """미체결 주문 전체 취소"""
    try:
        exchange.cancel_all_orders(symbol)
        logger.info(f"미체결 주문 전체 취소: {symbol}")
    except Exception as e:
        logger.warning(f"주문 취소 실패: {e}")
