"""
크레딧 테이블 마이그레이션 스크립트.

실행: python migrate_credits.py
"""
import database
import models

def migrate():
    engine = database.engine

    # 테이블 생성 (이미 있으면 무시)
    models.UserCredit.__table__.create(bind=engine, checkfirst=True)
    models.CreditTransaction.__table__.create(bind=engine, checkfirst=True)
    models.PaymentOrder.__table__.create(bind=engine, checkfirst=True)

    print("Credit tables created successfully.")

    # 기존 활성 사용자에게 크레딧 초기화
    import credit_service
    with database.get_db_session() as db:
        users = db.query(models.User).filter(models.User.is_active == True).all()
        count = 0
        for user in users:
            existing = db.query(models.UserCredit).filter(
                models.UserCredit.user_id == user.id
            ).first()
            if not existing:
                credit_service.ensure_user_credit(db, user.id)
                count += 1
        print(f"Initialized credits for {count} existing active users.")


if __name__ == "__main__":
    migrate()
