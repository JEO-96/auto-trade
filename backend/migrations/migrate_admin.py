"""
마이그레이션: is_admin 컬럼 추가 및 관리자 계정 설정

실행 방법:
    cd backend
    python migrate_admin.py
"""
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine


def migrate():
    with engine.connect() as conn:
        # 1. is_admin 컬럼 추가 (이미 존재하면 무시)
        conn.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
        """))
        print("[OK] is_admin 컬럼 추가 완료")

        # 2. id=3 사용자를 관리자로 설정
        result = conn.execute(text("""
            UPDATE users SET is_admin = TRUE WHERE id = 3;
        """))
        if result.rowcount > 0:
            print(f"[OK] id=3 사용자를 관리자로 설정 완료 (affected rows: {result.rowcount})")
        else:
            print("[WARN] id=3 사용자를 찾을 수 없습니다")

        conn.commit()
        print("[DONE] 마이그레이션 완료")


if __name__ == "__main__":
    migrate()
