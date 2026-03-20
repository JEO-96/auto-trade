"""
Migration: Add kakao_refresh_token column to users table.
Safe to run multiple times (IF NOT EXISTS check).
"""
from dotenv import load_dotenv
load_dotenv()

import database

def migrate():
    with database.engine.connect() as conn:
        try:
            conn.execute(database.text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS kakao_refresh_token VARCHAR"
            ))
            conn.commit()
            print("[OK] kakao_refresh_token 컬럼 추가 완료")
        except Exception as e:
            print(f"[SKIP] {e}")

    print("[DONE] 마이그레이션 완료")

if __name__ == "__main__":
    from sqlalchemy import text as _text
    database.text = _text
    migrate()
