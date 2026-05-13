from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .types import CandidateSnapshot


class MarketDataProvider(Protocol):
    async def top_candidates(self, limit: int) -> list[CandidateSnapshot]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class FixtureMarketDataProvider:
    def __init__(self, snapshots: Iterable[CandidateSnapshot]) -> None:
        self._snapshots = list(snapshots)

    async def top_candidates(self, limit: int) -> list[CandidateSnapshot]:
        return self._snapshots[:limit]

    async def close(self) -> None:
        return None


def _float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(str(row.get(key, default)).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _text(row: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return str(value)
    return default


def candidate_from_kis_rows(
    symbol: str,
    price_row: dict,
    rank_row: dict | None = None,
) -> CandidateSnapshot:
    rank_row = rank_row or {}
    price = _float(price_row, "stck_prpr")
    change_pct = _float(price_row, "prdy_ctrt")
    previous_close = price / (1 + (change_pct / 100.0)) if price > 0 and change_pct > -99 else 0.0
    trading_value = _float(price_row, "acml_tr_pbmn")
    volume_ratio = max(_float(price_row, "prdy_vol_vrss_acml_vol_rate") / 100.0, 0.0)
    symbol_from_row = _text(price_row, "stck_shrn_iscd", "mksc_shrn_iscd", default=symbol)

    return CandidateSnapshot(
        symbol=symbol_from_row or symbol,
        name=_text(price_row, "hts_kor_isnm", "prdt_name", default=symbol),
        price=price,
        previous_close=previous_close,
        trading_value_5m=trading_value,
        trading_value_ratio=max(volume_ratio, _float(rank_row, "data_rank", 0.0) and volume_ratio, 1.0),
        volume_ratio=max(volume_ratio, 1.0),
        execution_strength=_float(price_row, "cttr"),
        vwap=_float(price_row, "wghn_avrg_stck_prc", price),
        intraday_high=_float(price_row, "stck_hgpr", price),
        pivot_high=_float(price_row, "stck_hgpr", price),
        pullback_low=_float(price_row, "stck_lwpr", price),
        atr_1m=max(price * 0.0015, 1.0),
        atr_3m=max(price * 0.0030, 1.0),
        bid=_float(price_row, "bidp1", price),
        ask=_float(price_row, "askp1", price),
        bid_depth=_float(price_row, "total_bidp_rsqn"),
        ask_depth=_float(price_row, "total_askp_rsqn"),
        is_vi_caution=_float(price_row, "vi_stnd_prc") > 0,
        is_halted=_text(price_row, "trht_yn", default="N") == "Y",
    )


class KisRestMarketDataProvider:
    def __init__(self, client) -> None:
        self.client = client

    async def top_candidates(self, limit: int) -> list[CandidateSnapshot]:
        rank_rows = await self.client.volume_rank(limit=limit)
        snapshots: list[CandidateSnapshot] = []
        seen: set[str] = set()
        for row in rank_rows:
            symbol = _text(row, "mksc_shrn_iscd", "stck_shrn_iscd")
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            price_row = await self.client.current_price(symbol)
            snapshots.append(candidate_from_kis_rows(symbol, price_row, row))
        return snapshots

    async def close(self) -> None:
        await self.client.close()
