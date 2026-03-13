"""
포지션 영속화 모듈 — DB 기반 포지션 저장/복구/정리 및 봇 활성 상태 관리.

bot_manager.py에서 분리된 DB-centric 포지션 관리 함수들.
"""
import logging

import database
import models

logger = logging.getLogger(__name__)


def save_positions_to_db(bot_id: int, active_positions: dict) -> None:
    """현재 보유 포지션을 DB에 저장 (atomic delete+insert)"""
    with database.get_db_session() as db:
        try:
            # 단일 트랜잭션 내에서 삭제+삽입 (중간 크래시 시 전체 롤백)
            db.begin_nested()
            db.query(models.ActivePosition).filter(models.ActivePosition.bot_id == bot_id).delete()
            for symbol, pos in active_positions.items():
                db.add(models.ActivePosition(
                    bot_id=bot_id,
                    symbol=symbol,
                    position_amount=pos['position_amount'],
                    entry_price=pos['entry_price'],
                    stop_loss=pos['stop_loss'],
                    take_profit=pos['take_profit'],
                ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("[Bot %d] Failed to save positions: %s", bot_id, e)


def load_positions_from_db(bot_id: int) -> dict:
    """DB에서 포지션 복구"""
    positions: dict = {}
    with database.get_db_session() as db:
        try:
            rows = db.query(models.ActivePosition).filter(
                models.ActivePosition.bot_id == bot_id
            ).all()
            for row in rows:
                positions[row.symbol] = {
                    'position_amount': row.position_amount,
                    'entry_price': row.entry_price,
                    'stop_loss': row.stop_loss,
                    'take_profit': row.take_profit,
                }
            if positions:
                logger.info("[Bot %d] Recovered %d positions from DB", bot_id, len(positions))
        except Exception as e:
            logger.error("[Bot %d] Failed to load positions: %s", bot_id, e)
    return positions


def clear_positions_from_db(bot_id: int) -> None:
    """봇 정지 시 DB 포지션 정리"""
    with database.get_db_session() as db:
        try:
            db.query(models.ActivePosition).filter(models.ActivePosition.bot_id == bot_id).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("[Bot %d] Failed to clear positions: %s", bot_id, e)


def set_bot_active(bot_id: int, active: bool) -> None:
    """DB의 is_active 플래그를 업데이트"""
    with database.get_db_session() as db:
        try:
            bot = db.query(models.BotConfig).filter(models.BotConfig.id == bot_id).first()
            if bot:
                bot.is_active = active
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error("[Bot %d] Failed to update is_active: %s", bot_id, e)
