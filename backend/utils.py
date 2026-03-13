"""
utils.py - 공통 유틸리티 함수

여러 모듈에서 반복되는 작은 헬퍼 함수를 모아둡니다.
"""
import json
from typing import Any


def safe_json_loads(data: str | None, default: Any = None) -> Any:
    """JSON 문자열을 파싱. 빈 값이면 default 반환."""
    if not data:
        return default
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def parse_symbols(symbol_str: str) -> list[str]:
    """쉼표로 구분된 심볼 문자열을 리스트로 파싱."""
    return [s.strip() for s in symbol_str.split(',') if s.strip()]


def mask_nickname(name: str | None) -> str:
    """닉네임 익명화 (첫 글자 + **)."""
    if not name:
        return "익명"
    return name[0] + "**" if len(name) >= 1 else "익명"
