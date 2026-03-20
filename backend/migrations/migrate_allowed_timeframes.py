"""
마이그레이션: allowed_timeframes 테이블 생성 및 기본 데이터 삽입

관리자가 허용한 캔들 주기만 사용자가 선택할 수 있도록 설정합니다.

실행 방법:
    cd backend
    python migrate_allowed_timeframes.py
"""
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine

# 기본 허용 타임프레임 (기존 프론트엔드 BOT_TIMEFRAMES와 동일)
DEFAULT_TIMEFRAMES = [
    ("1m", "1분", 1),
    ("5m", "5분", 2),
    ("15m", "15분", 3),
    ("1h", "1시간", 4),
    ("4h", "4시간", 5),
    ("1d", "1일", 6),
]


def migrate():
    with engine.connect() as conn:
        # 1. allowed_timeframes 테이블 생성
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS allowed_timeframes (
                id SERIAL PRIMARY KEY,
                timeframe VARCHAR NOT NULL UNIQUE,
                label VARCHAR NOT NULL,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """))
        print("[OK] allowed_timeframes 테이블 생성 완료")

        # 2. 인덱스 생성
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_allowed_timeframes_id ON allowed_timeframes (id);
        """))
        print("[OK] 인덱스 생성 완료")

        # 3. 기본 데이터 삽입 (이미 존재하면 무시)
        for tf, label, order in DEFAULT_TIMEFRAMES:
            result = conn.execute(text("""
                INSERT INTO allowed_timeframes (timeframe, label, display_order, is_active)
                VALUES (:tf, :label, :order, TRUE)
                ON CONFLICT (timeframe) DO NOTHING;
            """), {"tf": tf, "label": label, "order": order})
            if result.rowcount > 0:
                print(f"  [+] {tf} ({label}) 추가됨")
            else:
                print(f"  [-] {tf} ({label}) 이미 존재")

        conn.commit()
        print("[DONE] 마이그레이션 완료")


if __name__ == "__main__":
    migrate()
