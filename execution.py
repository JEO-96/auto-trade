import config

class ExecutionEngine:
    def __init__(self, paper_trading=True):
        self.paper_trading = paper_trading
        print(f"Execution Engine initialized. Paper Trading: {self.paper_trading}")
        # In a real environment, initialize exchange API clients for execution here
        
    def execute_buy(self, symbol, price, amount_usd, is_market=True):
        """
        Executes a Buy order.
        """
        if self.paper_trading:
            amount = amount_usd / price if price > 0 else 0
            print(f"[PAPER] BUY executed for {symbol} at {price:.2f}. Amount: {amount:.4f}")
            return {"status": "success", "price": price, "amount": amount}
        else:
            print("Live trading is currently inactive. Set paper_trading=False and implement actual exchange API call here.")
            return None

    def execute_sell(self, symbol, price, amount, reason="Take Profit"):
        """
        Executes a Sell order (Full Exit).
        """
        if self.paper_trading:
            pnl_usd = price * amount
            print(f"[PAPER] SELL ({reason}) executed for {symbol} at {price:.2f}. Returns: {pnl_usd:.2f} USD")
            return {"status": "success", "price": price}
        else:
            print("Live trading is currently inactive. Implement actual exchange API call here.")
            return None

    def check_active_orders(self):
        """
        Check if pending orders are filled (e.g., limit orders).
        For paper trading, we assume market orders execute immediately.
        """
        return []
