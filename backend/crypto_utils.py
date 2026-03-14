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
