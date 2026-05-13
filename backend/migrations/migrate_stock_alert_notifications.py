"""Migration: users 테이블에 주식 추천 알림 설정 컬럼 추가."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from database import engine

logger = logging.getLogger(__name__)


def migrate() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "notification_stock_alert" in columns:
        logger.info("notification_stock_alert column already exists, skipping")
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN notification_stock_alert BOOLEAN DEFAULT FALSE"
            )
        )
    logger.info("Added notification_stock_alert column to users table")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate()
