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
) -> list[MarketCandidate]:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.price > 0 and candidate.quote_volume >= min_quote_volume
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
