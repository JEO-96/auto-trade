from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List
from datetime import date, datetime
import models, schemas
import credit_service
import bot_manager
from dependencies import get_db, get_admin_user, get_user_or_404

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=schemas.AdminDashboardResponse)
def get_admin_dashboard(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """관리자 대시보드 통계 (봇 현황, 매출, 시스템 헬스)"""
    today_start = datetime.combine(date.today(), datetime.min.time())

    # --- Users ---
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    active_users = db.query(func.count(models.User.id)).filter(models.User.is_active == True).scalar() or 0
    pending_users = db.query(func.count(models.User.id)).filter(models.User.is_active == False).scalar() or 0
    new_today = db.query(func.count(models.User.id)).filter(models.User.created_at >= today_start).scalar() or 0

    # --- Bots ---
    total_configs = db.query(func.count(models.BotConfig.id)).scalar() or 0
    live_bots_db = db.query(func.count(models.BotConfig.id)).filter(
        models.BotConfig.is_active == True,
        models.BotConfig.paper_trading_mode == False,
    ).scalar() or 0
    paper_bots_db = db.query(func.count(models.BotConfig.id)).filter(
        models.BotConfig.is_active == True,
        models.BotConfig.paper_trading_mode == True,
    ).scalar() or 0
    running_now = len([t for t in bot_manager.active_bots.values() if not t.done()])

    # --- Trades ---
    total_trades = db.query(func.count(models.TradeLog.id)).scalar() or 0
    total_pnl = db.query(func.coalesce(func.sum(models.TradeLog.pnl), 0.0)).scalar() or 0.0

    # TradeLog.timestamp is a string column, filter by string comparison
    today_str = date.today().isoformat()
    today_trades = db.query(func.count(models.TradeLog.id)).filter(
        models.TradeLog.timestamp >= today_str
    ).scalar() or 0
    today_pnl = db.query(func.coalesce(func.sum(models.TradeLog.pnl), 0.0)).filter(
        models.TradeLog.timestamp >= today_str
    ).scalar() or 0.0

    # --- Revenue ---
    def sum_by_tx_type(tx_type: str) -> float:
        result = db.query(func.coalesce(func.sum(models.CreditTransaction.amount), 0.0)).filter(
            models.CreditTransaction.tx_type == tx_type
        ).scalar()
        return float(result or 0.0)

    total_credit_purchased = sum_by_tx_type("purchase")
    total_profit_fees = abs(sum_by_tx_type("profit_fee"))  # profit_fee is negative (deduction)
    total_loss_refunds = sum_by_tx_type("loss_refund")
    net_revenue = total_profit_fees - total_loss_refunds

    # --- System ---
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return schemas.AdminDashboardResponse(
        users=schemas.AdminDashboardUsers(
            total=total_users,
            active=active_users,
            pending=pending_users,
            new_today=new_today,
        ),
        bots=schemas.AdminDashboardBots(
            total_configs=total_configs,
            running_now=running_now,
            live_bots=live_bots_db,
            paper_bots=paper_bots_db,
        ),
        trades=schemas.AdminDashboardTrades(
            total_trades=total_trades,
            today_trades=today_trades,
            total_pnl=float(total_pnl),
            today_pnl=float(today_pnl),
        ),
        revenue=schemas.AdminDashboardRevenue(
            total_credit_purchased=float(total_credit_purchased),
            total_profit_fees=float(total_profit_fees),
            total_loss_refunds=float(total_loss_refunds),
            net_revenue=float(net_revenue),
        ),
        system=schemas.AdminDashboardSystem(
            active_bot_count=running_now,
            db_connection_ok=db_ok,
            uptime_info="Server running",
        ),
    )


@router.get("/users", response_model=List[schemas.AdminUserResponse])
def list_all_users(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """전체 사용자 목록 조회 (관리자 전용)"""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return users


@router.get("/users/pending", response_model=List[schemas.AdminUserResponse])
def list_pending_users(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """승인 대기 중인 사용자 목록 조회 (is_active=False)"""
    users = (
        db.query(models.User)
        .filter(models.User.is_active == False)
        .order_by(models.User.created_at.desc())
        .all()
    )
    return users


@router.post("/users/{user_id}/approve", response_model=schemas.AdminUserResponse)
def approve_user(
    user_id: int,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """사용자 승인 (is_active=True)"""
    user = get_user_or_404(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    # 승인 시 크레딧 초기화 (이미 있으면 무시)
    credit_service.ensure_user_credit(db, user.id)
    return user


@router.post("/users/{user_id}/reject", response_model=schemas.AdminUserResponse)
def reject_user(
    user_id: int,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """사용자 거부 (is_active=False)"""
    user = get_user_or_404(db, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
