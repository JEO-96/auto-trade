"""
크레딧 서비스 — 잔액 관리 및 매매 수수료 처리.

핵심 정책:
- 회원가입 시 1000 크레딧 지급
- 실매매 수익 시: 수익금의 10% 크레딧 차감
- 실매매 손실 시: 손실금의 10% 크레딧 환불
- 크레딧 잔액 0 이하 시 실매매 봇 시작 불가
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

import database
import models

logger = logging.getLogger(__name__)

SIGNUP_BONUS = 1000.0
PROFIT_FEE_RATE = 0.10   # 수익의 10%
LOSS_REFUND_RATE = 0.10   # 손실의 10%


def ensure_user_credit(db: Session, user_id: int) -> models.UserCredit:
    """유저 크레딧 레코드가 없으면 생성 (가입 보너스 포함)"""
    credit = db.query(models.UserCredit).filter(
        models.UserCredit.user_id == user_id
    ).first()
    if credit:
        return credit

    credit = models.UserCredit(
        user_id=user_id,
        balance=SIGNUP_BONUS,
        total_earned=SIGNUP_BONUS,
        total_spent=0.0,
    )
    db.add(credit)
    db.flush()

    tx = models.CreditTransaction(
        user_id=user_id,
        amount=SIGNUP_BONUS,
        balance_after=SIGNUP_BONUS,
        tx_type="signup_bonus",
        description="회원가입 보너스 크레딧",
    )
    db.add(tx)
    db.commit()
    db.refresh(credit)

    logger.info("[Credit] User %d: signup bonus %.0f credits", user_id, SIGNUP_BONUS)
    return credit


def get_balance(db: Session, user_id: int) -> models.UserCredit:
    """크레딧 잔액 조회 (없으면 생성)"""
    return ensure_user_credit(db, user_id)


def process_trade_pnl(
    user_id: int,
    pnl: float,
    trade_log_id: Optional[int] = None,
) -> None:
    """
    매매 완료 후 PnL에 따른 크레딧 처리.
    - pnl > 0 (수익): 수익의 10% 차감
    - pnl < 0 (손실): 손실의 10% 환불
    - pnl == 0: 처리 없음
    """
    if pnl == 0:
        return

    with database.get_db_session() as db:
        try:
            credit = ensure_user_credit(db, user_id)

            if pnl > 0:
                fee = pnl * PROFIT_FEE_RATE
                credit.balance -= fee
                credit.total_spent += fee
                tx_type = "profit_fee"
                description = f"수익 수수료 (수익 {pnl:,.0f}원의 {PROFIT_FEE_RATE*100:.0f}%)"
            else:
                refund = abs(pnl) * LOSS_REFUND_RATE
                credit.balance += refund
                credit.total_earned += refund
                tx_type = "loss_refund"
                description = f"손실 환불 (손실 {abs(pnl):,.0f}원의 {LOSS_REFUND_RATE*100:.0f}%)"

            amount = -(pnl * PROFIT_FEE_RATE) if pnl > 0 else abs(pnl) * LOSS_REFUND_RATE

            tx = models.CreditTransaction(
                user_id=user_id,
                amount=amount,
                balance_after=credit.balance,
                tx_type=tx_type,
                reference_id=trade_log_id,
                description=description,
            )
            db.add(tx)
            db.commit()

            logger.info(
                "[Credit] User %d: %s %.1f credits (balance: %.1f)",
                user_id, tx_type, abs(amount), credit.balance,
            )
        except Exception as e:
            db.rollback()
            logger.error("[Credit] Failed to process PnL for user %d: %s", user_id, e)


def check_sufficient_credits(db: Session, user_id: int) -> bool:
    """실매매 봇 시작 전 크레딧 잔액 확인"""
    credit = ensure_user_credit(db, user_id)
    return credit.balance > 0


def admin_adjust(db: Session, user_id: int, amount: float, description: str = "") -> models.UserCredit:
    """관리자 수동 크레딧 조정"""
    credit = ensure_user_credit(db, user_id)
    credit.balance += amount
    if amount > 0:
        credit.total_earned += amount
    else:
        credit.total_spent += abs(amount)

    tx = models.CreditTransaction(
        user_id=user_id,
        amount=amount,
        balance_after=credit.balance,
        tx_type="admin_adjust",
        description=description or f"관리자 수동 조정 ({amount:+,.0f})",
    )
    db.add(tx)
    db.commit()
    db.refresh(credit)

    logger.info("[Credit] Admin adjust user %d: %+.0f (balance: %.0f)", user_id, amount, credit.balance)
    return credit
