from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketCandidate:
    symbol: str
    price: float
    quote_volume: float
    percentage: float
    score: float = 0.0


def select_top_markets(
    candidates: list[MarketCandidate],
    limit: int,
    min_quote_volume: float,
    max_percentage: float | None = None,
) -> list[MarketCandidate]:
    """Score & rank candidates.

    - ``min_quote_volume``: liquidity floor (filters illiquid alts / fake pumps).
    - ``max_percentage``: overheating cap. Candidates whose 24h change already
      exceeds this are excluded to avoid buying the top of a pump. ``None``
      disables the cap (legacy behaviour).
    """
    eligible = [
        candidate
        for candidate in candidates
        if candidate.price > 0
        and candidate.quote_volume >= min_quote_volume
        and (max_percentage is None or candidate.percentage <= max_percentage)
    ]
    scored = [
        MarketCandidate(
            symbol=candidate.symbol,
            price=candidate.price,
            quote_volume=candidate.quote_volume,
            percentage=candidate.percentage,
            score=_score(candidate),
        )
        for candidate in eligible
    ]
    return sorted(scored, key=lambda item: (-item.score, item.symbol))[:limit]


def _score(candidate: MarketCandidate) -> float:
    volume_factor = math.log10(max(candidate.quote_volume, 1.0))
    return candidate.percentage * volume_factor
