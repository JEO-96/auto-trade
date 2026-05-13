import httpx
import pytest

from core.scalping.kis_client import KisRestClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_kis_client_fetches_volume_rank():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/uapi/domestic-stock/v1/quotations/volume-rank"
        assert request.headers["tr_id"] == "FHPST01710000"
        return httpx.Response(200, json={"rt_cd": "0", "output": [{"mksc_shrn_iscd": "005930"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://test.kis") as client:
        kis = KisRestClient(app_key="key", app_secret="secret", access_token="token", client=client)
        rows = await kis.volume_rank(limit=20)

    assert rows == [{"mksc_shrn_iscd": "005930"}]


@pytest.mark.anyio
async def test_kis_client_raises_on_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rt_cd": "1", "msg1": "bad request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://test.kis") as client:
        kis = KisRestClient(app_key="key", app_secret="secret", access_token="token", client=client)
        with pytest.raises(RuntimeError, match="bad request"):
            await kis.current_price("005930")
