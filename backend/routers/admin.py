from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from dependencies import get_db, get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

# 전체 허용 타임프레임 목록 (관리자가 선택 가능한 값)
ALL_TIMEFRAMES = [
    {"timeframe": "1m", "label": "1분"},
    {"timeframe": "3m", "label": "3분"},
    {"timeframe": "5m", "label": "5분"},
    {"timeframe": "15m", "label": "15분"},
    {"timeframe": "30m", "label": "30분"},
    {"timeframe": "1h", "label": "1시간"},
    {"timeframe": "2h", "label": "2시간"},
    {"timeframe": "4h", "label": "4시간"},
    {"timeframe": "6h", "label": "6시간"},
    {"timeframe": "12h", "label": "12시간"},
    {"timeframe": "1d", "label": "1일"},
    {"timeframe": "1w", "label": "1주"},
]


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


# -------- 캔들 주기(타임프레임) 관리 --------

@router.get("/timeframes/all-options")
def get_all_timeframe_options(
    admin: models.User = Depends(get_admin_user),
):
    """관리자가 선택 가능한 전체 타임프레임 목록"""
    return ALL_TIMEFRAMES


@router.get("/timeframes", response_model=List[schemas.AllowedTimeframeResponse])
def list_allowed_timeframes_admin(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """허용된 캔들 주기 목록 조회 (관리자 전용, 비활성 포함)"""
    return (
        db.query(models.AllowedTimeframe)
        .order_by(models.AllowedTimeframe.display_order)
        .all()
    )


@router.post("/timeframes", response_model=schemas.AllowedTimeframeResponse, status_code=status.HTTP_201_CREATED)
def add_allowed_timeframe(
    req: schemas.AllowedTimeframeCreate,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """허용 캔들 주기 추가"""
    valid_values = {t["timeframe"] for t in ALL_TIMEFRAMES}
    if req.timeframe not in valid_values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"유효하지 않은 타임프레임: '{req.timeframe}'. 허용: {sorted(valid_values)}",
        )
    existing = db.query(models.AllowedTimeframe).filter(
        models.AllowedTimeframe.timeframe == req.timeframe
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{req.timeframe}'은(는) 이미 등록되어 있습니다.",
        )
    tf = models.AllowedTimeframe(
        timeframe=req.timeframe,
        label=req.label,
        display_order=req.display_order,
        is_active=req.is_active,
    )
    db.add(tf)
    db.commit()
    db.refresh(tf)
    return tf


@router.put("/timeframes/{timeframe_id}", response_model=schemas.AllowedTimeframeResponse)
def update_allowed_timeframe(
    timeframe_id: int,
    req: schemas.AllowedTimeframeUpdate,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """허용 캔들 주기 수정 (라벨, 순서, 활성/비활성)"""
    tf = db.query(models.AllowedTimeframe).filter(models.AllowedTimeframe.id == timeframe_id).first()
    if not tf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="타임프레임을 찾을 수 없습니다.")
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tf, field, value)
    db.commit()
    db.refresh(tf)
    return tf


@router.delete("/timeframes/{timeframe_id}")
def delete_allowed_timeframe(
    timeframe_id: int,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """허용 캔들 주기 삭제"""
    tf = db.query(models.AllowedTimeframe).filter(models.AllowedTimeframe.id == timeframe_id).first()
    if not tf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="타임프레임을 찾을 수 없습니다.")
    db.delete(tf)
    db.commit()
    return {"status": "success", "message": f"타임프레임 '{tf.timeframe}'이(가) 삭제되었습니다."}
