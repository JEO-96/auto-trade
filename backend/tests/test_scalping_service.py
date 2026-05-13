from datetime import datetime, timezone

import pytest

from core.scalping.config import ScalpingAlertConfig
from core.scalping.providers import FixtureMarketDataProvider, candidate_from_kis_rows
from core.scalping.service import ScalpingAlertService
from core.scalping.types import CandidateSnapshot


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _snapshot():
    return CandidateSnapshot(
        symbol="005930",
        name="삼성전자",
        price=70200,
        previous_close=69000,
        trading_value_5m=4_500_000_000,
        trading_value_ratio=4.2,
        volume_ratio=3.6,
        execution_strength=128.0,
        vwap=69600,
        intraday_high=70300,
        pivot_high=70000,
        pullback_low=69500,
        atr_1m=120,
        atr_3m=260,
        bid=70100,
        ask=70200,
        bid_depth=120_000,
        ask_depth=90_000,
        timestamp=datetime(2026, 5, 13, 9, 35, tzinfo=timezone.utc),
    )


@pytest.mark.anyio
async def test_service_dry_run_records_decision_without_sending():
    sent_messages: list[str] = []
    service = ScalpingAlertService(
        provider=FixtureMarketDataProvider([_snapshot()]),
        config=ScalpingAlertConfig(dry_run=True),
        send_message=lambda message: sent_messages.append(message),
        is_market_open=lambda: True,
    )

    result = await service.scan_once()

    assert result["evaluated"] == 1
    assert result["alerts"] == 1
    assert sent_messages == []
    assert service.status()["last_scan"]["alerts"] == 1


@pytest.mark.anyio
async def test_service_suppresses_when_market_closed():
    service = ScalpingAlertService(
        provider=FixtureMarketDataProvider([_snapshot()]),
        config=ScalpingAlertConfig(dry_run=False),
        send_message=lambda message: None,
        is_market_open=lambda: False,
    )

    result = await service.scan_once()

    assert result["evaluated"] == 0
    assert result["alerts"] == 0
    assert result["reason"] == "market closed"


def test_candidate_from_kis_rows_maps_price_and_rank_data():
    price_row = {
        "stck_shrn_iscd": "005930",
        "hts_kor_isnm": "삼성전자",
        "stck_prpr": "70200",
        "stck_oprc": "69000",
        "stck_hgpr": "70300",
        "stck_lwpr": "69500",
        "wghn_avrg_stck_prc": "69600",
        "askp1": "70200",
        "bidp1": "70100",
        "total_askp_rsqn": "90000",
        "total_bidp_rsqn": "120000",
        "cttr": "128.0",
        "prdy_vol_vrss_acml_vol_rate": "360.0",
        "acml_tr_pbmn": "4500000000",
        "prdy_ctrt": "1.74",
    }
    rank_row = {"data_rank": "1"}

    snap = candidate_from_kis_rows("005930", price_row, rank_row)

    assert snap.symbol == "005930"
    assert snap.name == "삼성전자"
    assert snap.price == 70200
    assert snap.trading_value_5m == 4_500_000_000
    assert snap.execution_strength == 128.0
