"""
Centralized encryption/decryption utilities for API keys and tokens.

Uses Fernet symmetric encryption backed by the FERNET_KEY environment variable.
All modules that need to encrypt or decrypt sensitive data should import from here.
"""
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from settings import settings

logger = logging.getLogger(__name__)

# Fernet 암호문은 항상 'gAAAAA'로 시작 (base64-encoded version byte)
FERNET_PREFIX = "gAAAAA"


def get_fernet() -> Fernet:
    key = settings.fernet_key
    if not key:
        raise RuntimeError(
            "FERNET_KEY environment variable is not set. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode())


def encrypt_key(text: str) -> str:
    f = get_fernet()
    return f.encrypt(text.encode()).decode()


def decrypt_key(text: str) -> str:
    f = get_fernet()
    return f.decrypt(text.encode()).decode()


def is_fernet_encrypted(text: str) -> bool:
    """Fernet 암호문 여부 판별 (prefix 기반)."""
    return text.startswith(FERNET_PREFIX)


def encrypt_token(token: Optional[str]) -> Optional[str]:
    """카카오 토큰 등 민감 문자열 암호화. None/빈 문자열은 그대로 반환."""
    if not token:
        return token
    # 이미 암호화된 값이면 중복 암호화 방지
    if is_fernet_encrypted(token):
        return token
    return encrypt_key(token)


def decrypt_token(encrypted: Optional[str]) -> Optional[str]:
    """암호화된 토큰 복호화. None/빈 문자열은 그대로 반환.
    암호화되지 않은 평문이면 그대로 반환 (마이그레이션 전 데이터 호환)."""
    if not encrypted:
        return encrypted
    if not is_fernet_encrypted(encrypted):
        # 평문 토큰 (아직 마이그레이션 안 된 데이터)
        return encrypted
    try:
        return decrypt_key(encrypted)
    except InvalidToken:
        logger.error("카카오 토큰 복호화 실패 — 잘못된 암호문이거나 FERNET_KEY 불일치")
        return None


def mask_api_key(key: str) -> str:
    """API 키 프리뷰용 마스킹 (첫 4자리 + ********)."""
    if len(key) >= 4:
        return key[:4] + "*" * 10
    return "****"


def create_exchange(exchange_name: str, api_key: str, api_secret: str):
    """거래소별 ccxt 인스턴스 생성 팩토리 함수."""
    import ccxt

    if exchange_name == "upbit":
        return ccxt.upbit({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"createMarketBuyOrderRequiresPrice": False},
        })
    elif exchange_name == "bithumb":
        return ccxt.bithumb({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"createMarketBuyOrderRequiresPrice": False},
        })
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}")


def fetch_exchange_balance(user_id: int, exchange_name: str, db) -> dict:
    """사용자의 거래소 잔고 조회. ExchangeKey 없으면 HTTPException 발생.

    Args:
        user_id: 사용자 ID
        exchange_name: 거래소 이름 (upbit, bithumb)
        db: SQLAlchemy Session

    Returns:
        ccxt raw balance dict (info, free, used, total 등 포함)

    Raises:
        HTTPException: API 키 미등록, 복호화 실패, 인증 실패, 네트워크 오류 등
    """
    import ccxt as ccxt_lib
    from fastapi import HTTPException, status

    # 순환 import 방지를 위해 지연 import
    import models

    exchange_label = exchange_name.upper()

    # 1. ExchangeKey 조회
    exchange_key = (
        db.query(models.ExchangeKey)
        .filter(
            models.ExchangeKey.user_id == user_id,
            models.ExchangeKey.exchange_name == exchange_name,
        )
        .first()
    )
    if not exchange_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"등록된 {exchange_label} API 키가 없습니다. 먼저 API 키를 등록해주세요.",
        )

    # 2. 복호화
    try:
        api_key = decrypt_key(exchange_key.api_key_encrypted)
        api_secret = decrypt_key(exchange_key.api_secret_encrypted)
    except Exception:
        logger.exception("Failed to decrypt exchange key for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 키 복호화에 실패했습니다. 키를 다시 등록해주세요.",
        )

    # 3. ccxt 인스턴스 생성 및 잔고 조회
    try:
        exchange = create_exchange(exchange_name, api_key, api_secret)
        raw_balance = exchange.fetch_balance()
    except ccxt_lib.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{exchange_label} API 인증에 실패했습니다. API 키와 시크릿을 확인해주세요.",
        )
    except ccxt_lib.NetworkError as exc:
        logger.warning("Network error fetching %s balance for user %s: %s", exchange_label, user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exchange_label} 서버와의 통신에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )
    except ccxt_lib.ExchangeError as exc:
        logger.warning("Exchange error fetching %s balance for user %s: %s", exchange_label, user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exchange_label} 거래소 오류: {exc}",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return raw_balance
