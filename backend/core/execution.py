import ccxt
import logging
import random
import time
from core import config

logger = logging.getLogger(__name__)

# 페이퍼 트레이딩 슬리피지 (0.05% ~ 0.15%)
PAPER_SLIPPAGE_MIN = 0.0005
PAPER_SLIPPAGE_MAX = 0.0015

# 실매매 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


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
            order = self._retry_order(
                lambda: self.exchange.create_market_buy_order(symbol, amount),
                symbol,
            )
            if order is None:
                return {"status": "error", "message": "Order failed after retries"}

            executed_price = self._resolve_executed_price(order, price)
            filled = order.get('filled')
            if filled is None or filled <= 0:
                filled = amount
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
            order = self._retry_order(
                lambda: self.exchange.create_market_sell_order(symbol, amount),
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
