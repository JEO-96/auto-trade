import ccxt
from core import config

class ExecutionEngine:
    def __init__(self, api_key=None, api_secret=None, exchange_name='binance', paper_trading=True):
        self.paper_trading = paper_trading
        self.exchange = None

        print(f"Execution Engine initialized. Paper Trading: {self.paper_trading}")

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
                print(f"[{exchange_name.upper()}] Live trading connected successfully!")
            except Exception as e:
                print(f"Failed to connect to {exchange_name}: {e}")
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
            print(f"[ERROR] Cannot execute BUY for {symbol}: price is {price}")
            return {"status": "error", "message": "Invalid price (<=0)"}

        amount = amount_usd / price

        if amount <= 0:
            print(f"[ERROR] Cannot execute BUY for {symbol}: computed amount is {amount}")
            return {"status": "error", "message": "Invalid amount (<=0)"}

        if self.paper_trading or not self.exchange:
            print(f"[PAPER] BUY executed for {symbol} at {price:.2f}. Amount: {amount:.4f}")
            return {"status": "success", "price": price, "amount": amount}
        else:
            try:
                # CCXT real market order
                print(f"[LIVE] Executing BUY Market order for {symbol}...")
                order = self.exchange.create_market_buy_order(symbol, amount)
                executed_price = self._resolve_executed_price(order, price)
                filled = order.get('filled')
                if filled is None or filled <= 0:
                    filled = amount
                print(f"[LIVE] BUY Order Successful! ID: {order['id']}")
                return {"status": "success", "price": executed_price, "amount": filled}
            except Exception as e:
                print(f"[LIVE] Error executing BUY: {e}")
                return {"status": "error", "message": str(e)}

    def execute_sell(self, symbol, price, amount, reason="Take Profit"):
        """
        Executes a Sell order (Full Exit).
        """
        if amount <= 0:
            print(f"[ERROR] Cannot execute SELL for {symbol}: amount is {amount}")
            return {"status": "error", "message": "Invalid amount (<=0)"}

        if self.paper_trading or not self.exchange:
            pnl_usd = price * amount
            print(f"[PAPER] SELL ({reason}) executed for {symbol} at {price:.2f}. Returns: {pnl_usd:.2f} USD")
            return {"status": "success", "price": price}
        else:
            try:
                print(f"[LIVE] Executing SELL Market order for {symbol}...")
                order = self.exchange.create_market_sell_order(symbol, amount)
                executed_price = self._resolve_executed_price(order, price)
                print(f"[LIVE] SELL Order Successful! ID: {order['id']}")
                return {"status": "success", "price": executed_price}
            except Exception as e:
                print(f"[LIVE] Error executing SELL: {e}")
                return {"status": "error", "message": str(e)}

    def check_active_orders(self):
        """
        Check if pending orders are filled (e.g., limit orders).
        For paper trading, we assume market orders execute immediately.
        """
        return []
