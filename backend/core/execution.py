import ccxt
import logging
import random
from core import config

logger = logging.getLogger(__name__)

# 페이퍼 트레이딩 슬리피지 (0.05% ~ 0.15%)
PAPER_SLIPPAGE_MIN = 0.0005
PAPER_SLIPPAGE_MAX = 0.0015

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
            except Exception as e:
                logger.error("Failed to connect to %s: %s", exchange_name, e)
                self.exchange = None

    @staticmethod
    def _resolve_executed_price(order: dict, fallback_price: float) -> float:
        """
        Safely extract the executed price from a CCXT order response.
        Handles cases where 'average' or 'price' may be 0, None, or missing.
        A value of 0.0 is treated as invalid (no exchange fills at price 0).
        """
        average = order.get('average')
        if average is not None and average > 0:
            return float(average)
        price = order.get('price')
        if price is not None and price > 0:
            return float(price)
        return fallback_price

    def execute_buy(self, symbol, price, amount_usd, is_market=True):
        """
        Executes a Buy order.
        """
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
            try:
                # CCXT real market order
                logger.info("[LIVE] Executing BUY Market order for %s...", symbol)
                order = self.exchange.create_market_buy_order(symbol, amount)
                executed_price = self._resolve_executed_price(order, price)
                filled = order.get('filled')
                if filled is None or filled <= 0:
                    filled = amount
                logger.info("[LIVE] BUY Order Successful! ID: %s", order['id'])
                return {"status": "success", "price": executed_price, "amount": filled}
            except Exception as e:
                logger.error("[LIVE] Error executing BUY: %s", e)
                return {"status": "error", "message": str(e)}

    def execute_sell(self, symbol, price, amount, reason="Take Profit"):
        """
        Executes a Sell order (Full Exit).
        """
        if amount <= 0:
            logger.error("Cannot execute SELL for %s: amount is %s", symbol, amount)
            return {"status": "error", "message": "Invalid amount (<=0)"}

        if self.paper_trading or not self.exchange:
            # 슬리피지 적용 (매도는 불리하게 → 가격 하락)
            slippage = random.uniform(PAPER_SLIPPAGE_MIN, PAPER_SLIPPAGE_MAX)
            fill_price = price * (1 - slippage)
            pnl_usd = fill_price * amount
            logger.info("[PAPER] SELL (%s) executed for %s at %.2f (slip %.3f%%). Returns: %.2f USD", reason, symbol, fill_price, slippage * 100, pnl_usd)
            return {"status": "success", "price": fill_price}
        else:
            try:
                logger.info("[LIVE] Executing SELL Market order for %s...", symbol)
                order = self.exchange.create_market_sell_order(symbol, amount)
                executed_price = self._resolve_executed_price(order, price)
                logger.info("[LIVE] SELL Order Successful! ID: %s", order['id'])
                return {"status": "success", "price": executed_price}
            except Exception as e:
                logger.error("[LIVE] Error executing SELL: %s", e)
                return {"status": "error", "message": str(e)}

    def check_active_orders(self):
        """
        Check if pending orders are filled (e.g., limit orders).
        For paper trading, we assume market orders execute immediately.
        """
        return []
