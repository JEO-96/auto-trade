"""
카카오 OAuth 서비스 — 토큰 교환 및 사용자 정보 조회.

routers/auth.py에서 분리된 Kakao API 호출 로직.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from settings import settings

logger = logging.getLogger(__name__)

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


@dataclass
class KakaoTokenResult:
    access_token: str
    refresh_token: Optional[str]


@dataclass
class KakaoUserInfo:
    kakao_id: str
    email: Optional[str]
    nickname: Optional[str]


async def exchange_code_for_tokens(code: str, redirect_uri: str) -> KakaoTokenResult:
    """카카오 인가 코드 → 액세스/리프레시 토큰 교환."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(KAKAO_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": settings.kakao_rest_api_key,
            "redirect_uri": redirect_uri,
            "code": code,
        })

    if resp.status_code != 200:
        logger.warning("Kakao token error: %s", resp.text)
        raise KakaoAuthError("Authentication failed")

    data = resp.json()
    return KakaoTokenResult(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
    )


async def get_user_info(kakao_token: str) -> KakaoUserInfo:
    """카카오 액세스 토큰으로 사용자 정보 조회."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            KAKAO_USER_INFO_URL,
            headers={"Authorization": f"Bearer {kakao_token}"},
        )

    if resp.status_code != 200:
        raise KakaoAuthError("Failed to get Kakao user info")

    user_json = resp.json()
    kakao_account = user_json.get("kakao_account", {})
    properties = user_json.get("properties", {})

    return KakaoUserInfo(
        kakao_id=str(user_json["id"]),
        email=kakao_account.get("email"),
        nickname=properties.get("nickname"),
    )


async def verify_token(kakao_token: str) -> str:
    """카카오 토큰 유효성 검증 후 kakao_id 반환."""
    info = await get_user_info(kakao_token)
    return info.kakao_id


class KakaoAuthError(Exception):
    """카카오 인증 과정에서 발생하는 오류."""
