import logging
import random
import time

import ccxt

from constants import (
    MAX_RETRIES,
    PAPER_SLIPPAGE_MAX,
    PAPER_SLIPPAGE_MIN,
    RETRY_DELAY,
)
from core import config

logger = logging.getLogger(__name__)


class ExecutionEngine:
    def __init__(self, api_key=None, api_secret=None, exchange_name='binance', paper_trading=True):
        self.paper_trading = paper_trading
        self.exchange = None

        logger.info("Execution Engine initialized. Paper Trading: %s", self.paper_trading)

        if not self.paper_trading and api_key and api_secret:
            try:
                exchange_class = getattr(ccxt, exchange_name.lower())
                self.exchange = exchange_class({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                })
                # Check connection
                self.exchange.fetch_balance()
                logger.info("[%s] Live trading connected successfully!", exchange_name.upper())
            except ccxt.AuthenticationError as e:
                logger.error("Authentication failed for %s: %s", exchange_name, e)
                self.exchange = None
            except Exception as e:
                logger.error("Failed to connect to %s: %s", exchange_name, e)
                self.exchange = None

    def is_live_ready(self) -> bool:
        """실매매 가능 상태인지 확인"""
        return not self.paper_trading and self.exchange is not None

    def fetch_total_balance_krw(self) -> float | None:
        """업비트 계좌의 총 자산(KRW 환산)을 조회. 실패 시 None 반환."""
        if not self.exchange:
            return None
        try:
            balance = self.exchange.fetch_balance()
            total_krw: float = 0.0

            # KRW 현금
            krw_free = float(balance.get('KRW', {}).get('total', 0) or 0)
            total_krw += krw_free

            # 보유 코인 평가금액
            for currency, info in balance.items():
                if currency in ('KRW', 'info', 'free', 'used', 'total', 'timestamp', 'datetime'):
                    continue
                total_amount = float(info.get('total', 0) or 0)
                if total_amount <= 0:
                    continue
                try:
                    ticker = self.exchange.fetch_ticker(f"{currency}/KRW")
                    price = ticker.get('last', 0) or 0
                    total_krw += total_amount * float(price)
                except Exception:
                    pass  # 마이너 코인 등 조회 실패 시 무시

            return total_krw
        except Exception as e:
            logger.error("[ExecutionEngine] Failed to fetch balance: %s", e)
            return None

    @staticmethod
    def _resolve_executed_price(order: dict, fallback_price: float) -> float:
        """
        Safely extract the executed price from a CCXT order response.
        A value of 0.0 is treated as invalid (no exchange fills at price 0).
        """
        average = order.get('average')
        if average is not None and average > 0:
            return float(average)
        price = order.get('price')
        if price is not None and price > 0:
            return float(price)
        return fallback_price

    def _retry_order(self, order_func, symbol: str, retries: int = MAX_RETRIES) -> dict | None:
        """네트워크/일시적 오류 시 재시도"""
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                return order_func()
            except ccxt.NetworkError as e:
                last_error = e
                logger.warning("[LIVE] Network error on attempt %d/%d for %s: %s", attempt, retries, symbol, e)
                if attempt < retries:
                    time.sleep(RETRY_DELAY * attempt)
            except ccxt.ExchangeNotAvailable as e:
                last_error = e
                logger.warning("[LIVE] Exchange unavailable on attempt %d/%d for %s: %s", attempt, retries, symbol, e)
                if attempt < retries:
                    time.sleep(RETRY_DELAY * attempt)
            except ccxt.InvalidOrder as e:
                # 주문 자체가 잘못된 경우 재시도 의미 없음
                logger.error("[LIVE] Invalid order for %s: %s", symbol, e)
                return None
            except ccxt.InsufficientFunds as e:
                logger.error("[LIVE] Insufficient funds for %s: %s", symbol, e)
                return None
            except ccxt.AuthenticationError as e:
                logger.error("[LIVE] Auth error for %s: %s", symbol, e)
                return None
            except Exception as e:
                logger.error("[LIVE] Unexpected error for %s: %s", symbol, e)
                return None

        logger.error("[LIVE] All %d retries exhausted for %s. Last error: %s", retries, symbol, last_error)
        return None

    def execute_buy(self, symbol, price, amount_usd, is_market=True):
        """Executes a Buy order."""
        if price <= 0:
            logger.error("Cannot execute BUY for %s: price is %s", symbol, price)
            return {"status": "error", "message": "Invalid price (<=0)"}

        amount = amount_usd / price

        if amount <= 0:
            logger.error("Cannot execute BUY for %s: computed amount is %s", symbol, amount)
            return {"status": "error", "message": "Invalid amount (<=0)"}

        if self.paper_trading or not self.exchange:
            # 슬리피지 적용 (매수는 불리하게 → 가격 상승)
            slippage = random.uniform(PAPER_SLIPPAGE_MIN, PAPER_SLIPPAGE_MAX)
            fill_price = price * (1 + slippage)
            amount = amount_usd / fill_price
            logger.info("[PAPER] BUY executed for %s at %.2f (slip %.3f%%). Amount: %.4f", symbol, fill_price, slippage * 100, amount)
            return {"status": "success", "price": fill_price, "amount": amount}
        else:
            # Upbit 시장가 매수: KRW 금액(cost)을 직접 전달해야 시장가로 처리됨
            # qty+price를 함께 전달하면 지정가(limit)로 처리되어 잔고 부족 에러 발생
            _cost = amount_usd  # KRW 금액
            order = self._retry_order(
                lambda: self.exchange.create_order(symbol, 'market', 'buy', _cost),
                symbol,
            )
            if order is None:
                return {"status": "error", "message": "Order failed after retries"}

            executed_price = self._resolve_executed_price(order, price)
            filled = order.get('filled')
            if filled is None or filled <= 0:
                # cost / executed_price로 수량 추정
                filled = amount_usd / executed_price if executed_price > 0 else amount
            logger.info("[LIVE] BUY Order Successful! ID: %s, Price: %.2f, Amount: %.4f",
                        order.get('id', 'N/A'), executed_price, filled)
            return {"status": "success", "price": executed_price, "amount": float(filled)}

    def execute_sell(self, symbol, price, amount, reason="Take Profit"):
        """Executes a Sell order (Full Exit)."""
        if amount <= 0:
            logger.error("Cannot execute SELL for %s: amount is %s", symbol, amount)
            return {"status": "error", "message": "Invalid amount (<=0)"}

        if self.paper_trading or not self.exchange:
            # 슬리피지 적용 (매도는 불리하게 → 가격 하락)
            slippage = random.uniform(PAPER_SLIPPAGE_MIN, PAPER_SLIPPAGE_MAX)
            fill_price = price * (1 - slippage)
            logger.info("[PAPER] SELL (%s) for %s at %.2f (slip %.3f%%)", reason, symbol, fill_price, slippage * 100)
            return {"status": "success", "price": fill_price, "amount": amount}
        else:
            _amount = amount
            order = self._retry_order(
                lambda: self.exchange.create_order(symbol, 'market', 'sell', _amount),
                symbol,
            )
            if order is None:
                return {"status": "error", "message": "Sell order failed after retries"}

            executed_price = self._resolve_executed_price(order, price)
            filled = order.get('filled')
            if filled is None or filled <= 0:
                filled = amount
            logger.info("[LIVE] SELL Order Successful! ID: %s, Price: %.2f, Reason: %s",
                        order.get('id', 'N/A'), executed_price, reason)
            return {"status": "success", "price": executed_price, "amount": float(filled)}

    def detect_existing_holdings(self, symbols: list[str]) -> dict[str, dict]:
        """거래소 잔고에서 봇 심볼에 해당하는 기존 보유 코인을 감지.

        Returns:
            {symbol: {'amount': float, 'avg_buy_price': float}}
            보유량이 0이거나 거래소 연결이 안 된 경우 빈 dict 반환.
        """
        if not self.exchange:
            return {}

        try:
            balance = self.exchange.fetch_balance()
        except Exception as e:
            logger.error("[ExecutionEngine] Failed to fetch balance for holding detection: %s", e)
            return {}

        # symbol → currency 매핑 (예: "BTC/KRW" → "BTC")
        symbol_to_currency: dict[str, str] = {}
        for sym in symbols:
            parts = sym.split('/')
            if parts:
                symbol_to_currency[sym] = parts[0]

        holdings: dict[str, dict] = {}

        # 업비트 raw info에서 avg_buy_price 추출
        raw_info: list[dict] = balance.get('info', [])
        avg_prices: dict[str, float] = {}
        if isinstance(raw_info, list):
            for item in raw_info:
                currency = item.get('currency', '')
                avg_price = float(item.get('avg_buy_price', 0) or 0)
                if currency and avg_price > 0:
                    avg_prices[currency] = avg_price

        for sym, currency in symbol_to_currency.items():
            total_amount = float(balance.get(currency, {}).get('total', 0) or 0)
            if total_amount <= 0:
                continue

            avg_buy_price = avg_prices.get(currency, 0)
            if avg_buy_price <= 0:
                # avg_buy_price를 못 가져오면 현재가 fallback
                try:
                    ticker = self.exchange.fetch_ticker(sym)
                    avg_buy_price = float(ticker.get('last', 0) or 0)
                except Exception:
                    logger.warning("[ExecutionEngine] Cannot get price for %s, skipping", sym)
                    continue

            holdings[sym] = {
                'amount': total_amount,
                'avg_buy_price': avg_buy_price,
            }
            logger.info(
                "[ExecutionEngine] Detected holding: %s qty=%.6f avg_price=%.0f",
                sym, total_amount, avg_buy_price,
            )

        return holdings
