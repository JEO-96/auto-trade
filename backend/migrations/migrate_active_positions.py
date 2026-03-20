"""
Migration: active_positions 테이블 생성
봇의 보유 포지션을 DB에 저장하여 서버 재시작 시 복구할 수 있도록 함.
"""
import database
import models

def migrate():
    # active_positions 테이블 생성
    models.ActivePosition.__table__.create(bind=database.engine, checkfirst=True)
    print("✓ active_positions 테이블 생성 완료")

    # 기존 봇의 is_active를 False로 초기화 (깨끗한 상태에서 시작)
    db = database.SessionLocal()
    try:
        updated = db.query(models.BotConfig).filter(
            models.BotConfig.is_active == True
        ).update({models.BotConfig.is_active: False})
        db.commit()
        if updated:
            print(f"✓ {updated}개 봇의 is_active를 False로 초기화")
        else:
            print("✓ 초기화할 봇 없음")
    finally:
        db.close()

    print("마이그레이션 완료!")


if __name__ == "__main__":
    migrate()
