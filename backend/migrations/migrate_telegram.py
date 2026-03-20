"""
마이그레이션: users 테이블에 telegram_chat_id 컬럼 추가
"""
from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    with engine.connect() as conn:
        # telegram_chat_id 컬럼 추가
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR NULL"
            ))
            conn.commit()
            logger.info("Added telegram_chat_id column to users table")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info("telegram_chat_id column already exists, skipping")
                conn.rollback()
            else:
                raise

    logger.info("Migration completed successfully")


if __name__ == "__main__":
    migrate()
