"""
마이그레이션: bot_configs 테이블에 exchange_name 컬럼 추가
- 기본값: 'upbit' (기존 봇은 모두 업비트)
- 멱등성 보장: 이미 컬럼이 존재하면 스킵
"""
import logging

from database import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    with engine.connect() as conn:
        # bot_configs 테이블에 exchange_name 컬럼 존재 여부 확인
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'bot_configs' AND column_name = 'exchange_name'
        """))
        if result.fetchone():
            logger.info("bot_configs.exchange_name 컬럼이 이미 존재합니다. 스킵합니다.")
        else:
            conn.execute(text("""
                ALTER TABLE bot_configs
                ADD COLUMN exchange_name VARCHAR DEFAULT 'upbit'
            """))
            conn.commit()
            logger.info("bot_configs.exchange_name 컬럼 추가 완료 (기본값: 'upbit')")

    logger.info("마이그레이션 완료.")


if __name__ == "__main__":
    migrate()
