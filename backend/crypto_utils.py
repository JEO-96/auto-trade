"""
Centralized encryption/decryption utilities for API keys.

Uses Fernet symmetric encryption backed by the FERNET_KEY environment variable.
All modules that need to encrypt or decrypt exchange API keys should import from here.
"""
from cryptography.fernet import Fernet

from settings import settings


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
