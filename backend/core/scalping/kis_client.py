from __future__ import annotations

import httpx


class KisRestClient:
    def __init__(
        self,
        *,
        app_key: str,
        app_secret: str,
        access_token: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://openapi.koreainvestment.com:9443",
            timeout=10.0,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(self, path: str, tr_id: str, params: dict[str, str]) -> list[dict] | dict:
        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }
        response = await self._client.get(path, headers=headers, params=params)
        response.raise_for_status()
        body = response.json()
        if body.get("rt_cd") not in (None, "0"):
            raise RuntimeError(body.get("msg1") or "KIS API request failed")
        output = body.get("output")
        if output is None:
            return []
        return output

    async def volume_rank(self, limit: int) -> list[dict]:
        output = await self._get(
            "/uapi/domestic-stock/v1/quotations/volume-rank",
            "FHPST01710000",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "1",
                "FID_BLNG_CLS_CODE": "3",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "1111111111",
                "FID_INPUT_PRICE_1": "1000",
                "FID_INPUT_PRICE_2": "1000000",
                "FID_VOL_CNT": "100000",
                "FID_INPUT_DATE_1": "",
            },
        )
        rows = output if isinstance(output, list) else [output]
        return rows[:limit]

    async def fluctuation_rank(self, limit: int) -> list[dict]:
        output = await self._get(
            "/uapi/domestic-stock/v1/ranking/fluctuation",
            "FHPST01700000",
            {
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code": "20170",
                "fid_input_iscd": "0000",
                "fid_rank_sort_cls_code": "0000",
                "fid_input_cnt_1": str(limit),
                "fid_prc_cls_code": "0",
                "fid_input_price_1": "1000",
                "fid_input_price_2": "1000000",
                "fid_vol_cnt": "100000",
                "fid_trgt_cls_code": "0",
                "fid_trgt_exls_cls_code": "0",
                "fid_div_cls_code": "0",
                "fid_rsfl_rate1": "0",
                "fid_rsfl_rate2": "30",
            },
        )
        rows = output if isinstance(output, list) else [output]
        return rows[:limit]

    async def current_price(self, symbol: str) -> dict:
        output = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
            },
        )
        if isinstance(output, list):
            return output[0] if output else {}
        return output
