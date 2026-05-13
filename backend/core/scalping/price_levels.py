from __future__ import annotations

import math
from typing import Literal

from .config import ScalpingAlertConfig
from .types import CandidateSnapshot, PriceLevels

RoundMode = Literal["floor", "ceil", "nearest"]


def _tick_size(price: float) -> int:
    if price < 2_000:
        return 1
    if price < 5_000:
        return 5
    if price < 20_000:
        return 10
    if price < 50_000:
        return 50
    if price < 200_000:
        return 100
    if price < 500_000:
        return 500
    return 1_000


def round_price_to_tick(price: float, mode: RoundMode = "nearest") -> int:
    tick = _tick_size(max(price, 1))
    if mode == "floor":
        return int(math.floor(price / tick) * tick)
    if mode == "ceil":
        return int(math.ceil(price / tick) * tick)
    return int(round(price / tick) * tick)


def _pct(from_price: float, to_price: float) -> float:
    if from_price <= 0:
        return 0.0
    return ((to_price - from_price) / from_price) * 100.0


def calculate_price_levels(
    snapshot: CandidateSnapshot,
    config: ScalpingAlertConfig,
) -> tuple[PriceLevels | None, str | None]:
    if snapshot.price <= 0:
        return None, "invalid price"

    entry_anchor = max(snapshot.price, snapshot.pivot_high, snapshot.vwap)
    entry_low = round_price_to_tick(entry_anchor, "ceil")
    entry_high_raw = max(
        entry_low,
        min(snapshot.price * 1.003, entry_low + max(snapshot.atr_1m, 1) * 0.8),
    )
    entry_high = round_price_to_tick(entry_high_raw, "ceil")
    entry_mid = (entry_low + entry_high) / 2.0

    volatility_stop = entry_mid - max(snapshot.atr_1m * 1.2, snapshot.atr_3m * 0.7)
    stop_candidates = [
        ("pivot reclaim", snapshot.pivot_high * 0.997),
        ("pullback low", snapshot.pullback_low * 0.997),
        ("VWAP", snapshot.vwap * 0.997),
        ("volatility band", volatility_stop),
    ]
    valid_candidates = [(reason, price) for reason, price in stop_candidates if 0 < price < entry_low]
    if not valid_candidates:
        return None, "no valid stop"

    invalidation_reason, stop_raw = min(valid_candidates, key=lambda item: item[1])
    stop = round_price_to_tick(stop_raw, "floor")
    risk_per_share = entry_mid - stop
    if risk_per_share <= 0:
        return None, "invalid risk"

    risk_pct = abs(_pct(entry_mid, stop))
    if risk_pct > config.max_stop_pct:
        return None, "stop distance too wide"
    if risk_pct < config.min_stop_pct:
        return None, "stop distance too narrow"

    target1 = round_price_to_tick(entry_mid + risk_per_share, "ceil")
    target2 = round_price_to_tick(entry_mid + risk_per_share * 1.8, "ceil")
    if target1 <= entry_high:
        return None, "target too close"

    return PriceLevels(
        entry_low=float(entry_low),
        entry_high=float(entry_high),
        stop=float(stop),
        target1=float(target1),
        target2=float(target2),
        risk_pct=round(risk_pct, 2),
        reward1_pct=round(_pct(entry_mid, target1), 2),
        reward2_pct=round(_pct(entry_mid, target2), 2),
        invalidation_reason=invalidation_reason,
    ), None
