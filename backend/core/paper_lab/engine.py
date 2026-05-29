from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.paper_lab.allocator import allocate_equal_capital


@dataclass
class PaperPosition:
    symbol: str
    qty: float
    entry_price: float
    peak_price: float = 0.0  # high-water mark since entry, for trailing exits


@dataclass
class PaperTrade:
    symbol: str
    qty: float
    entry_price: float
    exit_price: float

    @property
    def realized_pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.qty


@dataclass
class SymbolBucket:
    symbol: str
    cash: float
    position: Optional[PaperPosition] = None
    trades: list[PaperTrade] = field(default_factory=list)

    def buy(self, price: float, qty: Optional[float] = None) -> None:
        if price <= 0:
            raise ValueError("price must be positive")
        if qty is not None and qty <= 0:
            raise ValueError("qty must be positive")
        if self.position is not None:
            raise ValueError(f"{self.symbol} already has an open position")
        effective_qty = qty if qty is not None else self.cash / price
        cost = price * effective_qty
        if cost > self.cash + 1e-9:
            raise ValueError(
                f"Insufficient cash for {self.symbol}: have {self.cash}, need {cost}"
            )
        self.cash -= cost
        self.position = PaperPosition(
            symbol=self.symbol, qty=effective_qty, entry_price=price, peak_price=price
        )

    def sell(self, price: float) -> PaperTrade:
        if price <= 0:
            raise ValueError("price must be positive")
        if self.position is None:
            raise ValueError(f"{self.symbol} has no open position")
        trade = PaperTrade(
            symbol=self.symbol,
            qty=self.position.qty,
            entry_price=self.position.entry_price,
            exit_price=price,
        )
        self.cash += price * self.position.qty
        self.trades.append(trade)
        self.position = None
        return trade

    @property
    def realized_pnl(self) -> float:
        return sum(t.realized_pnl for t in self.trades)

    def unrealized_pnl(self, mark_price: float) -> float:
        if self.position is None:
            return 0.0
        return (mark_price - self.position.entry_price) * self.position.qty

    def equity(self, mark_price: float) -> float:
        position_value = self.position.qty * mark_price if self.position else 0.0
        return self.cash + position_value


@dataclass
class PaperLabState:
    buckets: dict[str, SymbolBucket]

    def summary(self, mark_prices: dict[str, float]) -> dict:
        total_equity = 0.0
        total_realized = 0.0
        total_unrealized = 0.0
        open_positions = 0
        for symbol, bucket in self.buckets.items():
            if bucket.position is not None and symbol not in mark_prices:
                raise KeyError(f"Missing mark price for open position: {symbol}")
            price = mark_prices.get(symbol, 0.0)
            total_equity += bucket.equity(price)
            total_realized += bucket.realized_pnl
            total_unrealized += bucket.unrealized_pnl(price)
            if bucket.position is not None:
                open_positions += 1
        return {
            "total_equity": total_equity,
            "realized_pnl": total_realized,
            "unrealized_pnl": total_unrealized,
            "open_position_count": open_positions,
        }

    def position_details(self, mark_prices: dict[str, float]) -> list[dict]:
        details: list[dict] = []
        for symbol, bucket in self.buckets.items():
            if bucket.position is None:
                details.append(
                    {
                        "symbol": symbol,
                        "cash": bucket.cash,
                        "position_open": False,
                        "realized_pnl": bucket.realized_pnl,
                    }
                )
                continue
            if symbol not in mark_prices:
                raise KeyError(f"Missing mark price for open position: {symbol}")
            mark_price = mark_prices[symbol]
            entry_value = bucket.position.entry_price * bucket.position.qty
            unrealized_pnl = bucket.unrealized_pnl(mark_price)
            details.append(
                {
                    "symbol": symbol,
                    "cash": bucket.cash,
                    "position_open": True,
                    "qty": bucket.position.qty,
                    "entry_price": bucket.position.entry_price,
                    "mark_price": mark_price,
                    "position_value": bucket.position.qty * mark_price,
                    "unrealized_pnl": unrealized_pnl,
                    "return_pct": (unrealized_pnl / entry_value * 100) if entry_value else 0.0,
                    "realized_pnl": bucket.realized_pnl,
                }
            )
        return details


class PaperLabEngine:
    def __init__(self, symbols: list[str], total_capital: float) -> None:
        allocations = allocate_equal_capital(symbols, total_capital)
        buckets = {sym: SymbolBucket(symbol=sym, cash=alloc) for sym, alloc in allocations.items()}
        self.state = PaperLabState(buckets=buckets)

    def buy(self, symbol: str, price: float, qty: Optional[float] = None) -> None:
        self._bucket(symbol).buy(price, qty)

    def sell(self, symbol: str, price: float) -> PaperTrade:
        return self._bucket(symbol).sell(price)

    def summary(self, mark_prices: dict[str, float]) -> dict:
        return self.state.summary(mark_prices)

    def position_details(self, mark_prices: dict[str, float]) -> list[dict]:
        return self.state.position_details(mark_prices)

    def to_dict(self) -> dict:
        return {
            "buckets": {
                symbol: {
                    "cash": bucket.cash,
                    "position": (
                        {
                            "symbol": bucket.position.symbol,
                            "qty": bucket.position.qty,
                            "entry_price": bucket.position.entry_price,
                            "peak_price": bucket.position.peak_price,
                        }
                        if bucket.position
                        else None
                    ),
                    "trades": [
                        {
                            "symbol": trade.symbol,
                            "qty": trade.qty,
                            "entry_price": trade.entry_price,
                            "exit_price": trade.exit_price,
                        }
                        for trade in bucket.trades
                    ],
                }
                for symbol, bucket in self.state.buckets.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperLabEngine":
        engine = cls.__new__(cls)
        buckets: dict[str, SymbolBucket] = {}
        for symbol, bucket_data in data["buckets"].items():
            position_data = bucket_data.get("position")
            position = (
                PaperPosition(
                    symbol=position_data["symbol"],
                    qty=float(position_data["qty"]),
                    entry_price=float(position_data["entry_price"]),
                    peak_price=float(
                        position_data.get("peak_price", position_data["entry_price"])
                    ),
                )
                if position_data
                else None
            )
            trades = [
                PaperTrade(
                    symbol=trade["symbol"],
                    qty=float(trade["qty"]),
                    entry_price=float(trade["entry_price"]),
                    exit_price=float(trade["exit_price"]),
                )
                for trade in bucket_data.get("trades", [])
            ]
            buckets[symbol] = SymbolBucket(
                symbol=symbol,
                cash=float(bucket_data["cash"]),
                position=position,
                trades=trades,
            )
        engine.state = PaperLabState(buckets=buckets)
        return engine

    def _bucket(self, symbol: str) -> SymbolBucket:
        if symbol not in self.state.buckets:
            raise KeyError(f"Symbol {symbol} not in experiment")
        return self.state.buckets[symbol]
