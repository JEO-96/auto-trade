"""
테스트 공통 픽스처 — In-memory SQLite 기반 DB 세션 제공.

실제 PostgreSQL이나 외부 서비스 없이 독립적으로 테스트 가능.
"""
import sys
import os
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# backend 디렉토리를 Python path에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# settings 모듈이 .env를 요구하므로 환경변수로 필수값 주입 (import 전에 설정)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "test")

from database import Base
import models  # noqa: F401 — 모델 등록을 위해 import 필요


# In-memory SQLite 엔진 (테스트 전용)
TEST_ENGINE = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def setup_test_db():
    """매 테스트마다 깨끗한 DB 스키마 생성 및 정리."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    """테스트용 DB 세션 — 테스트 종료 시 자동 롤백."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@contextmanager
def fake_get_db_session_factory(session):
    """database.get_db_session()을 대체할 컨텍스트 매니저 팩토리.

    position_manager, credit_service 등이 내부적으로 사용하는
    `with database.get_db_session() as db:` 패턴을 테스트 세션으로 교체.
    """
    yield session


@pytest.fixture
def mock_get_db_session(db_session):
    """database.get_db_session을 테스트 세션으로 교체하는 픽스처.

    반환값: (패치할 함수, db_session) 튜플.
    사용 예: monkeypatch.setattr(database, "get_db_session", mock_fn)
    """
    @contextmanager
    def _mock():
        yield db_session

    return _mock, db_session


@pytest.fixture
def sample_user(db_session):
    """테스트용 사용자 생성."""
    user = models.User(
        id=1,
        email="test@example.com",
        nickname="tester",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_bot_config(db_session, sample_user):
    """테스트용 봇 설정 생성."""
    bot = models.BotConfig(
        id=1,
        user_id=sample_user.id,
        symbol="BTC/KRW",
        timeframe="4h",
        strategy_name="james_pro_stable",
        paper_trading_mode=True,
        allocated_capital=1_000_000.0,
        is_active=False,
    )
    db_session.add(bot)
    db_session.commit()
    db_session.refresh(bot)
    return bot
