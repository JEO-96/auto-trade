"""크레딧 관련 API 엔드포인트 (잔액 조회, 거래 내역, 토스 결제)"""
import logging
import uuid
from datetime import datetime
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import credit_service
import models
import schemas
from dependencies import get_db, get_current_user, get_admin_user
from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/credits", tags=["credits"])

TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"
MIN_CHARGE_AMOUNT = 1000      # 최소 충전 금액 (원)
MAX_CHARGE_AMOUNT = 1000000   # 최대 충전 금액 (원)


@router.get("/", response_model=schemas.CreditBalanceResponse)
def get_my_credits(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """내 크레딧 잔액 조회"""
    credit = credit_service.get_balance(db, current_user.id)
    return schemas.CreditBalanceResponse(
        balance=credit.balance,
        total_earned=credit.total_earned,
        total_spent=credit.total_spent,
    )


@router.get("/history", response_model=schemas.CreditTransactionListResponse)
def get_credit_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """크레딧 거래 내역 조회 (페이징)"""
    query = db.query(models.CreditTransaction).filter(
        models.CreditTransaction.user_id == current_user.id
    ).order_by(models.CreditTransaction.created_at.desc())

    total = query.count()
    transactions = query.offset((page - 1) * page_size).limit(page_size).all()

    return schemas.CreditTransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )


# ────────────────────────────────────────────
# 토스페이먼츠 결제
# ────────────────────────────────────────────

@router.post("/payment/order", response_model=schemas.PaymentOrderResponse)
def create_payment_order(
    req: schemas.PaymentOrderCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """결제 주문 생성 — 프론트에서 토스 결제창 호출 전에 호출"""
    if not settings.toss_client_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="결제 서비스가 설정되지 않았습니다.")

    if req.amount < MIN_CHARGE_AMOUNT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"최소 충전 금액은 {MIN_CHARGE_AMOUNT:,}원입니다.")
    if req.amount > MAX_CHARGE_AMOUNT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"최대 충전 금액은 {MAX_CHARGE_AMOUNT:,}원입니다.")

    order_id = f"credit_{current_user.id}_{uuid.uuid4().hex[:12]}"
    credits = req.amount  # 1원 = 1크레딧

    order = models.PaymentOrder(
        user_id=current_user.id,
        order_id=order_id,
        amount=req.amount,
        credits=credits,
        status="pending",
    )
    db.add(order)
    db.commit()

    logger.info("[Payment] User %d created order %s: %d원 = %d credits",
                current_user.id, order_id, req.amount, credits)

    return schemas.PaymentOrderResponse(
        order_id=order_id,
        amount=req.amount,
        credits=credits,
        toss_client_key=settings.toss_client_key,
    )


@router.post("/payment/confirm", response_model=schemas.CreditBalanceResponse)
async def confirm_payment(
    req: schemas.PaymentConfirmRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """토스 결제 승인 — 프론트 성공 콜백에서 호출"""
    # 1. 주문 조회 및 검증
    order = db.query(models.PaymentOrder).filter(
        models.PaymentOrder.order_id == req.order_id,
        models.PaymentOrder.user_id == current_user.id,
    ).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="주문을 찾을 수 없습니다.")
    if order.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"이미 처리된 주문입니다. (상태: {order.status})")
    if order.amount != req.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="결제 금액이 일치하지 않습니다.")

    # 2. 토스 결제 승인 API 호출
    import base64
    secret_b64 = base64.b64encode(f"{settings.toss_secret_key}:".encode()).decode()

    async with httpx.AsyncClient(timeout=15.0) as client:
        toss_resp = await client.post(
            TOSS_CONFIRM_URL,
            headers={
                "Authorization": f"Basic {secret_b64}",
                "Content-Type": "application/json",
            },
            json={
                "paymentKey": req.payment_key,
                "orderId": req.order_id,
                "amount": req.amount,
            },
        )

    if toss_resp.status_code != 200:
        error_data = toss_resp.json()
        error_msg = error_data.get("message", "결제 승인에 실패했습니다.")
        logger.error("[Payment] Toss confirm failed for order %s: %s", req.order_id, error_data)
        order.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # 3. 결제 성공 — 주문 상태 업데이트
    toss_data = toss_resp.json()
    order.status = "confirmed"
    order.payment_key = req.payment_key
    order.method = toss_data.get("method", "")
    order.confirmed_at = datetime.utcnow()
    db.commit()

    # 4. 크레딧 충전
    credit = credit_service.get_balance(db, current_user.id)
    credit.balance += order.credits
    credit.total_earned += order.credits

    tx = models.CreditTransaction(
        user_id=current_user.id,
        amount=order.credits,
        balance_after=credit.balance,
        tx_type="purchase",
        description=f"크레딧 충전 ({order.amount:,}원, {order.method or '토스'})",
    )
    db.add(tx)
    db.commit()
    db.refresh(credit)

    logger.info("[Payment] User %d charged %d credits (order %s, %d원)",
                current_user.id, order.credits, order.order_id, order.amount)

    return schemas.CreditBalanceResponse(
        balance=credit.balance,
        total_earned=credit.total_earned,
        total_spent=credit.total_spent,
    )


@router.get("/payment/history", response_model=List[schemas.PaymentHistoryResponse])
def get_payment_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """결제 내역 조회"""
    orders = db.query(models.PaymentOrder).filter(
        models.PaymentOrder.user_id == current_user.id
    ).order_by(models.PaymentOrder.created_at.desc()).limit(50).all()
    return orders


# ────────────────────────────────────────────
# 관리자 전용
# ────────────────────────────────────────────

@router.get("/admin/overview", response_model=List[schemas.AdminCreditOverview])
def admin_credit_overview(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """전체 유저 크레딧 현황 (관리자)"""
    credits = (
        db.query(models.UserCredit)
        .join(models.User, models.User.id == models.UserCredit.user_id)
        .all()
    )
    result = []
    for c in credits:
        user = db.query(models.User).filter(models.User.id == c.user_id).first()
        if user:
            result.append(schemas.AdminCreditOverview(
                user_id=user.id,
                email=user.email,
                nickname=user.nickname,
                balance=c.balance,
                total_earned=c.total_earned,
                total_spent=c.total_spent,
            ))
    return result


@router.post("/admin/{user_id}/adjust", response_model=schemas.CreditBalanceResponse)
def admin_adjust_credit(
    user_id: int,
    req: schemas.AdminCreditAdjust,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """관리자 수동 크레딧 조정"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    credit = credit_service.admin_adjust(db, user_id, req.amount, req.description)
    return schemas.CreditBalanceResponse(
        balance=credit.balance,
        total_earned=credit.total_earned,
        total_spent=credit.total_spent,
    )
