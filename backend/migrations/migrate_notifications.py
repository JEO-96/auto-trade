"""
마이그레이션: users 테이블에 알림 설정 컬럼 3개 추가
- notification_trade (매매 체결 알림)
- notification_bot_status (봇 시작/정지 알림)
- notification_system (시스템/공지 알림)
"""
from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    columns = [
        ("notification_trade", "BOOLEAN DEFAULT TRUE"),
        ("notification_bot_status", "BOOLEAN DEFAULT TRUE"),
        ("notification_system", "BOOLEAN DEFAULT TRUE"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns:
            try:
                conn.execute(text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                logger.info("Added %s column to users table", col_name)
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    logger.info("%s column already exists, skipping", col_name)
                    conn.rollback()
                else:
                    raise

    logger.info("Notification settings migration completed successfully")


if __name__ == "__main__":
    migrate()
