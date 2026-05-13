from core.scalping.kis_realtime import RealtimeSnapshotBuffer, parse_realtime_payload


def test_parse_realtime_trade_payload():
    payload = (
        "005930^093501^70200^2^1200^1.74^69600^69000^70300^69500^"
        "70200^70100^5000^1000000^4500000000^10^20^10^128.0"
    )

    row = parse_realtime_payload("H0STCNT0", payload)

    assert row["MKSC_SHRN_ISCD"] == "005930"
    assert row["STCK_PRPR"] == "70200"
    assert row["CTTR"] == "128.0"


def test_realtime_buffer_combines_trade_and_orderbook_rows():
    buffer = RealtimeSnapshotBuffer()
    trade_payload = (
        "005930^093501^70200^2^1200^1.74^69600^69000^70300^69500^"
        "70200^70100^5000^1000000^4500000000^10^20^10^128.0"
    )
    orderbook_payload = (
        "005930^093501^0^70200^70300^70400^70500^70600^70700^70800^70900^71000^71100^"
        "70100^70000^69900^69800^69700^69600^69500^69400^69300^69200^"
        "90000^1^1^1^1^1^1^1^1^1^120000"
    )

    buffer.update("H0STCNT0", trade_payload)
    buffer.update("H0STASP0", orderbook_payload)
    snap = buffer.to_candidate("005930")

    assert snap is not None
    assert snap.symbol == "005930"
    assert snap.price == 70200
    assert snap.bid_depth == 120000
    assert snap.ask_depth == 90000
