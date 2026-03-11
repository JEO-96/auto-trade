from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from dependencies import get_db, get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])


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
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reject", response_model=schemas.AdminUserResponse)
def reject_user(
    user_id: int,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """사용자 거부 (is_active=False)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
