from __future__ import annotations

from .providers import candidate_from_kis_rows
from .types import CandidateSnapshot

TRADE_TR_ID = "H0STCNT0"
ORDERBOOK_TR_ID = "H0STASP0"

TRADE_COLUMNS = [
    "MKSC_SHRN_ISCD",
    "STCK_CNTG_HOUR",
    "STCK_PRPR",
    "PRDY_VRSS_SIGN",
    "PRDY_VRSS",
    "PRDY_CTRT",
    "WGHN_AVRG_STCK_PRC",
    "STCK_OPRC",
    "STCK_HGPR",
    "STCK_LWPR",
    "ASKP1",
    "BIDP1",
    "CNTG_VOL",
    "ACML_VOL",
    "ACML_TR_PBMN",
    "SELN_CNTG_CSNU",
    "SHNU_CNTG_CSNU",
    "NTBY_CNTG_CSNU",
    "CTTR",
]

ORDERBOOK_COLUMNS = [
    "MKSC_SHRN_ISCD",
    "BSOP_HOUR",
    "HOUR_CLS_CODE",
    "ASKP1",
    "ASKP2",
    "ASKP3",
    "ASKP4",
    "ASKP5",
    "ASKP6",
    "ASKP7",
    "ASKP8",
    "ASKP9",
    "ASKP10",
    "BIDP1",
    "BIDP2",
    "BIDP3",
    "BIDP4",
    "BIDP5",
    "BIDP6",
    "BIDP7",
    "BIDP8",
    "BIDP9",
    "BIDP10",
    "TOTAL_ASKP_RSQN",
    "ASKP_RSQN1",
    "ASKP_RSQN2",
    "ASKP_RSQN3",
    "ASKP_RSQN4",
    "ASKP_RSQN5",
    "ASKP_RSQN6",
    "ASKP_RSQN7",
    "ASKP_RSQN8",
    "ASKP_RSQN9",
    "ASKP_RSQN10",
    "TOTAL_BIDP_RSQN",
]


def _normalize_payload(payload: str) -> str:
    if "|" in payload:
        return payload.rsplit("|", 1)[-1]
    return payload


def parse_realtime_payload(tr_id: str, payload: str) -> dict[str, str]:
    if tr_id == TRADE_TR_ID:
        columns = TRADE_COLUMNS
    elif tr_id == ORDERBOOK_TR_ID:
        columns = ORDERBOOK_COLUMNS
    else:
        raise ValueError(f"unsupported KIS realtime TR ID: {tr_id}")
    values = _normalize_payload(payload).split("^")
    row = {column: values[index] if index < len(values) else "" for index, column in enumerate(columns)}
    if tr_id == ORDERBOOK_TR_ID and not row.get("TOTAL_BIDP_RSQN") and values:
        row["TOTAL_BIDP_RSQN"] = values[-1]
    return row


def _lower_keys(row: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in row.items()}


class RealtimeSnapshotBuffer:
    def __init__(self) -> None:
        self._trades: dict[str, dict[str, str]] = {}
        self._orderbooks: dict[str, dict[str, str]] = {}

    def update(self, tr_id: str, payload: str) -> None:
        row = parse_realtime_payload(tr_id, payload)
        symbol = row["MKSC_SHRN_ISCD"]
        if tr_id == TRADE_TR_ID:
            self._trades[symbol] = row
        elif tr_id == ORDERBOOK_TR_ID:
            self._orderbooks[symbol] = row

    def to_candidate(self, symbol: str) -> CandidateSnapshot | None:
        trade = self._trades.get(symbol)
        if trade is None:
            return None
        merged = _lower_keys(trade)
        orderbook = self._orderbooks.get(symbol)
        if orderbook is not None:
            merged.update(_lower_keys(orderbook))
        return candidate_from_kis_rows(symbol, merged, None)
