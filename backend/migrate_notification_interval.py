"""
Migration: users 테이블에 notification_interval 컬럼 추가
- 정기 분석 피드백 주기 설정 (realtime, 4h, 12h, daily)
- 기본값: 'realtime' (매 캔들 마감마다)
"""

from sqlalchemy import text
from database import engine


def migrate():
    with engine.connect() as conn:
        # notification_interval 컬럼 추가
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN notification_interval VARCHAR DEFAULT 'realtime'"
            ))
            conn.commit()
            print("[OK] Added 'notification_interval' column to users table.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("[SKIP] 'notification_interval' column already exists.")
            else:
                raise


if __name__ == "__main__":
    migrate()
