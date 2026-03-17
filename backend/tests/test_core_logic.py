"""
핵심 로직 단위 테스트 — 봇 시작/정지, 포지션 저장.

모든 테스트는 in-memory SQLite를 사용하며 외부 서비스(ccxt, telegram 등) 없이 독립 실행됩니다.
"""
import sys
import os
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

import pytest

# backend 디렉토리를 Python path에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import database
import position_manager
import bot_manager


# ================================================================
# 1. 포지션 영속화 테스트 (test_position_manager)
# ================================================================

class TestPositionManager:
    """DB 기반 포지션 저장/복구/정리 로직 검증."""

    def test_save_and_load_positions(self, db_session, sample_bot_config):
        """포지션 저장 후 로드 시 동일한 데이터 반환."""
        bot_id = sample_bot_config.id
        positions = {
            "BTC/KRW": {
                "position_amount": 0.01,
                "entry_price": 50_000_000.0,
                "stop_loss": 48_000_000.0,
                "take_profit": 55_000_000.0,
            },
            "ETH/KRW": {
                "position_amount": 0.5,
                "entry_price": 3_000_000.0,
                "stop_loss": 2_800_000.0,
                "take_profit": 3_500_000.0,
            },
        }

        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            position_manager.save_positions_to_db(bot_id, positions)
            loaded = position_manager.load_positions_from_db(bot_id)

        assert len(loaded) == 2
        assert "BTC/KRW" in loaded
        assert "ETH/KRW" in loaded

        # BTC 포지션 정확성 검증
        btc = loaded["BTC/KRW"]
        assert btc["position_amount"] == pytest.approx(0.01)
        assert btc["entry_price"] == pytest.approx(50_000_000.0)
        assert btc["stop_loss"] == pytest.approx(48_000_000.0)
        assert btc["take_profit"] == pytest.approx(55_000_000.0)

        # ETH 포지션 정확성 검증
        eth = loaded["ETH/KRW"]
        assert eth["position_amount"] == pytest.approx(0.5)
        assert eth["entry_price"] == pytest.approx(3_000_000.0)

    def test_save_overwrites_previous(self, db_session, sample_bot_config):
        """저장 시 기존 포지션을 완전히 교체 (atomic delete+insert)."""
        bot_id = sample_bot_config.id

        positions_v1 = {
            "BTC/KRW": {
                "position_amount": 0.01,
                "entry_price": 50_000_000.0,
                "stop_loss": 48_000_000.0,
                "take_profit": 55_000_000.0,
            },
        }
        positions_v2 = {
            "ETH/KRW": {
                "position_amount": 1.0,
                "entry_price": 3_000_000.0,
                "stop_loss": 2_800_000.0,
                "take_profit": 3_500_000.0,
            },
        }

        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            position_manager.save_positions_to_db(bot_id, positions_v1)
            position_manager.save_positions_to_db(bot_id, positions_v2)
            loaded = position_manager.load_positions_from_db(bot_id)

        # v1의 BTC는 사라지고, v2의 ETH만 남아야 함
        assert "BTC/KRW" not in loaded
        assert "ETH/KRW" in loaded
        assert len(loaded) == 1

    def test_clear_positions(self, db_session, sample_bot_config):
        """클리어 후 빈 dict 반환."""
        bot_id = sample_bot_config.id
        positions = {
            "BTC/KRW": {
                "position_amount": 0.01,
                "entry_price": 50_000_000.0,
                "stop_loss": 48_000_000.0,
                "take_profit": 55_000_000.0,
            },
        }

        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            position_manager.save_positions_to_db(bot_id, positions)
            position_manager.clear_positions_from_db(bot_id)
            loaded = position_manager.load_positions_from_db(bot_id)

        assert loaded == {}

    def test_save_empty_positions(self, db_session, sample_bot_config):
        """빈 포지션 저장 시 DB에 레코드 없음."""
        bot_id = sample_bot_config.id

        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            position_manager.save_positions_to_db(bot_id, {})
            loaded = position_manager.load_positions_from_db(bot_id)

        assert loaded == {}

        # DB에 실제 레코드가 없는지 확인
        count = db_session.query(models.ActivePosition).filter(
            models.ActivePosition.bot_id == bot_id,
        ).count()
        assert count == 0

    def test_load_nonexistent_bot(self, db_session):
        """존재하지 않는 봇 ID로 로드 시 빈 dict 반환."""
        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            loaded = position_manager.load_positions_from_db(bot_id=9999)

        assert loaded == {}

    def test_set_bot_active(self, db_session, sample_bot_config):
        """봇 활성 상태 플래그 업데이트."""
        bot_id = sample_bot_config.id
        assert sample_bot_config.is_active is False

        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            position_manager.set_bot_active(bot_id, True)

        db_session.refresh(sample_bot_config)
        assert sample_bot_config.is_active is True

        with patch.object(database, "get_db_session", _mock_session):
            position_manager.set_bot_active(bot_id, False)

        db_session.refresh(sample_bot_config)
        assert sample_bot_config.is_active is False


# ================================================================
# 3. 봇 라이프사이클 테스트 (test_bot_lifecycle)
# ================================================================

class TestBotLifecycle:
    """봇 상태 관리 및 설정 로드 로직 검증."""

    def test_bot_status_stopped(self, sample_bot_config):
        """봇이 active_bots에 없으면 Stopped 상태."""
        # active_bots가 비어있는 상태에서 테스트
        bot_manager.active_bots.clear()

        status = bot_manager.get_bot_status(sample_bot_config.id)
        assert status == "Stopped"

    def test_bot_status_running(self, sample_bot_config):
        """봇이 active_bots에 있고 완료되지 않았으면 Running 상태."""
        bot_manager.active_bots.clear()

        mock_task = MagicMock()
        mock_task.done.return_value = False
        bot_manager.active_bots[sample_bot_config.id] = mock_task

        status = bot_manager.get_bot_status(sample_bot_config.id)
        assert status == "Running"

        # 정리
        bot_manager.active_bots.clear()

    def test_bot_status_done_task(self, sample_bot_config):
        """봇 태스크가 완료(done)되었으면 Stopped 상태."""
        bot_manager.active_bots.clear()

        mock_task = MagicMock()
        mock_task.done.return_value = True
        bot_manager.active_bots[sample_bot_config.id] = mock_task

        status = bot_manager.get_bot_status(sample_bot_config.id)
        assert status == "Stopped"

        # 정리
        bot_manager.active_bots.clear()

    def test_bot_config_loading(self, db_session, sample_bot_config):
        """봇 설정 로드 시 올바른 데이터 반환."""
        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            cfg = bot_manager._load_bot_config(sample_bot_config.id)

        assert cfg is not None
        assert cfg["symbols"] == ["BTC/KRW"]
        assert cfg["timeframe"] == "4h"
        assert cfg["liquid_capital"] == 1_000_000.0
        assert cfg["paper_trading"] is True
        assert cfg["strategy_name"] == "james_pro_stable"
        assert cfg["user_id"] == 1

    def test_bot_config_loading_multi_symbol(self, db_session, sample_user):
        """다중 심볼 봇 설정 로드."""
        bot = models.BotConfig(
            id=2,
            user_id=sample_user.id,
            symbol="BTC/KRW,ETH/KRW",
            timeframe="1h",
            strategy_name="momentum_stable",
            paper_trading_mode=True,
            allocated_capital=2_000_000.0,
            is_active=False,
        )
        db_session.add(bot)
        db_session.commit()

        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            cfg = bot_manager._load_bot_config(bot.id)

        assert cfg is not None
        assert cfg["symbols"] == ["BTC/KRW", "ETH/KRW"]
        assert cfg["liquid_capital"] == 2_000_000.0

    def test_bot_config_loading_not_found(self, db_session):
        """존재하지 않는 봇 ID 로드 시 None 반환."""
        @contextmanager
        def _mock_session():
            yield db_session

        with patch.object(database, "get_db_session", _mock_session):
            cfg = bot_manager._load_bot_config(9999)

        assert cfg is None

    def test_active_bots_dict_safe_access(self):
        """active_bots 딕셔너리 .get() 패턴으로 KeyError 방지."""
        bot_manager.active_bots.clear()

        # 존재하지 않는 키에 대해 .get()은 None 반환
        task = bot_manager.active_bots.get(12345)
        assert task is None

        # get_bot_status도 안전하게 동작
        status = bot_manager.get_bot_status(12345)
        assert status == "Stopped"


