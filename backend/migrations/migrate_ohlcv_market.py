"""마이그레이션: ohlcv_data 테이블에 market 컬럼 추가 + 유니크 제약 (market, symbol, timeframe, timestamp)로 확장.

- idempotent하게 작성
- 기존 row는 'crypto'로 백필
- 기존 unique constraint/index 안전하게 drop 후 재생성
- PostgreSQL 기준 (운영 DB)
"""
import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    with engine.connect() as conn:
        try:
            # 0) 테이블 존재 여부 가드 — 신규 환경에서는 SQLAlchemy create_all이 처리
            exists = conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'ohlcv_data'"
            )).first()
            if not exists:
                logger.warning("ohlcv_data 테이블이 없습니다. SQLAlchemy create_all 후 다시 실행하세요. 마이그레이션 skip.")
                return

            # 1) market 컬럼 추가 (없으면)
            conn.execute(text(
                "ALTER TABLE ohlcv_data ADD COLUMN IF NOT EXISTS market VARCHAR DEFAULT 'crypto' NOT NULL"
            ))
            logger.info("Step 1/5: market 컬럼 추가 (또는 이미 존재) 완료")

            # 2) 기존 row 백필 — market이 NULL/빈 문자열이면 'crypto'
            result = conn.execute(text(
                "UPDATE ohlcv_data SET market = 'crypto' WHERE market IS NULL OR market = ''"
            ))
            logger.info("Step 2/5: 기존 row 백필 완료 (rowcount=%s)", result.rowcount)

            # 3) 기존 유니크 제약/인덱스 제거 (있으면)
            conn.execute(text(
                "ALTER TABLE ohlcv_data DROP CONSTRAINT IF EXISTS uq_ohlcv_symbol_tf_ts"
            ))
            conn.execute(text(
                "DROP INDEX IF EXISTS ix_ohlcv_symbol_tf_ts"
            ))
            logger.info("Step 3/5: 구 unique constraint/index 제거 완료")

            # 4) 신규 유니크 제약 — (market, symbol, timeframe, timestamp)
            #    이미 존재하면 무시
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_ohlcv_market_symbol_tf_ts'
                    ) THEN
                        ALTER TABLE ohlcv_data
                        ADD CONSTRAINT uq_ohlcv_market_symbol_tf_ts
                        UNIQUE (market, symbol, timeframe, timestamp);
                    END IF;
                END
                $$;
            """))
            logger.info("Step 4/5: 신규 unique constraint 생성 완료")

            # 5) 신규 인덱스 — (market, symbol, timeframe, timestamp)
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_ohlcv_market_symbol_tf_ts "
                "ON ohlcv_data(market, symbol, timeframe, timestamp)"
            ))
            # market 단독 인덱스도 추가 (모델 정의 상 index=True 반영)
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_ohlcv_data_market ON ohlcv_data(market)"
            ))
            logger.info("Step 5/5: 신규 index 생성 완료")

            conn.commit()
            logger.info("Migration complete: ohlcv_data.market column + new unique key")
        except Exception as e:
            conn.rollback()
            logger.error("Migration failed: %s", e)
            raise


if __name__ == "__main__":
    run()
