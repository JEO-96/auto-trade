from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence


@dataclass(frozen=True)
class CandidateSnapshot:
    symbol: str
    name: str
    price: float
    previous_close: float
    trading_value_5m: float
    trading_value_ratio: float
    volume_ratio: float
    execution_strength: float
    vwap: float
    intraday_high: float
    pivot_high: float
    pullback_low: float
    atr_1m: float
    atr_3m: float
    bid: float
    ask: float
    bid_depth: float
    ask_depth: float
    is_vi_caution: bool = False
    is_halted: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def change_pct(self) -> float:
        if self.previous_close <= 0:
            return 0.0
        return ((self.price - self.previous_close) / self.previous_close) * 100.0

    @property
    def spread_pct(self) -> float:
        if self.price <= 0 or self.ask <= 0 or self.bid <= 0:
            return 100.0
        return ((self.ask - self.bid) / self.price) * 100.0

    @property
    def orderbook_imbalance(self) -> float:
        total = self.bid_depth + self.ask_depth
        if total <= 0:
            return 0.0
        return self.bid_depth / total


@dataclass(frozen=True)
class PriceLevels:
    entry_low: float
    entry_high: float
    stop: float
    target1: float
    target2: float
    risk_pct: float
    reward1_pct: float
    reward2_pct: float
    invalidation_reason: str

    @property
    def entry_mid(self) -> float:
        return (self.entry_low + self.entry_high) / 2.0


@dataclass(frozen=True)
class SignalDecision:
    symbol: str
    name: str
    should_alert: bool
    score: int
    grade: str
    reasons: Sequence[str]
    rejections: Sequence[str]
    levels: PriceLevels | None


@dataclass(frozen=True)
class AlertRecord:
    symbol: str
    name: str
    score: int
    grade: str
    message: str
    created_at: datetime
