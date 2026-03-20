"""
마이그레이션: system_settings 테이블 생성 + backtest_history에 title, start_date, end_date, commission_rate 컬럼 추가

사용법:
    cd backend
    python migrate_system_settings.py
"""
import json
from sqlalchemy import text
from database import engine, SessionLocal
from models import SystemSettings, BacktestHistory, Base


def migrate():
    # 1. system_settings 테이블 생성
    Base.metadata.create_all(bind=engine, tables=[SystemSettings.__table__])
    print("[OK] system_settings 테이블 생성 완료")

    # 2. backtest_history에 새 컬럼 추가 (이미 있으면 무시)
    new_columns = [
        ("title", "VARCHAR"),
        ("start_date", "VARCHAR"),
        ("end_date", "VARCHAR"),
        ("commission_rate", "FLOAT"),
    ]
    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(
                    f"ALTER TABLE backtest_history ADD COLUMN {col_name} {col_type}"
                ))
                conn.commit()
                print(f"[OK] backtest_history.{col_name} 컬럼 추가 완료")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"[SKIP] backtest_history.{col_name} 컬럼이 이미 존재합니다")
                else:
                    print(f"[WARN] backtest_history.{col_name} 컬럼 추가 실패: {e}")

    # 3. 기본 설정 삽입 (없을 때만)
    db = SessionLocal()
    try:
        existing = db.query(SystemSettings).filter(
            SystemSettings.key == "backtest_allowed_strategies"
        ).first()
        if not existing:
            default_strategies = [
                "momentum_breakout_basic",
                "momentum_breakout_pro_stable",
                "momentum_breakout_pro_aggressive",
                "momentum_breakout_elite",
                "steady_compounder",
                "james_basic",
                "james_pro_stable",
                "james_pro_aggressive",
                "james_pro_elite",
            ]
            db.add(SystemSettings(
                key="backtest_allowed_strategies",
                value=json.dumps(default_strategies),
            ))
            print("[OK] 기본 허용 전략 설정 삽입 완료")

        existing_tf = db.query(SystemSettings).filter(
            SystemSettings.key == "backtest_allowed_timeframes"
        ).first()
        if not existing_tf:
            default_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
            db.add(SystemSettings(
                key="backtest_allowed_timeframes",
                value=json.dumps(default_timeframes),
            ))
            print("[OK] 기본 허용 타임프레임 설정 삽입 완료")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 기본 설정 삽입 실패: {e}")
    finally:
        db.close()

    print("\n마이그레이션 완료!")


if __name__ == "__main__":
    migrate()
