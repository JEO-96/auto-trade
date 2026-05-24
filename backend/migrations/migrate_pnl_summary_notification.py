"""Migration: users 테이블에 PnL 요약 알림 설정 컬럼 추가."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from database import engine

logger = logging.getLogger(__name__)


def migrate() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "notification_pnl_summary" in columns:
        logger.info("notification_pnl_summary column already exists, skipping")
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN notification_pnl_summary BOOLEAN DEFAULT TRUE"
            )
        )
    logger.info("Added notification_pnl_summary column to users table")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate()
