import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import models
import schemas
from constants import MAX_USER_STRATEGIES
from core.strategy import STRATEGY_MAP
from dependencies import get_db, get_current_user
from utils import safe_json_loads

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/", response_model=schemas.UserStrategyResponse, status_code=status.HTTP_201_CREATED)
def create_user_strategy(
    req: schemas.UserStrategyCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """커스텀 전략 생성"""
    # 이름 길이 검증
    if not req.name or len(req.name.strip()) == 0:
        raise HTTPException(status_code=400, detail="전략 이름을 입력해주세요.")
    if len(req.name) > 50:
        raise HTTPException(status_code=400, detail="전략 이름은 50자 이하로 입력해주세요.")

    # 기본 전략 존재 확인
    if req.base_strategy_name not in STRATEGY_MAP:
        raise HTTPException(status_code=400, detail=f"알 수 없는 기본 전략: {req.base_strategy_name}")

    # 사용자당 전략 수 제한
    count = db.query(models.UserStrategy).filter(
        models.UserStrategy.user_id == current_user.id,
        models.UserStrategy.is_deleted == False,
    ).count()
    if count >= MAX_USER_STRATEGIES:
        raise HTTPException(status_code=400, detail=f"커스텀 전략은 최대 {MAX_USER_STRATEGIES}개까지 저장할 수 있습니다.")

    # 이름 중복 확인
    existing = db.query(models.UserStrategy).filter(
        models.UserStrategy.user_id == current_user.id,
        models.UserStrategy.name == req.name.strip(),
        models.UserStrategy.is_deleted == False,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 같은 이름의 전략이 있습니다.")

    strategy = models.UserStrategy(
        user_id=current_user.id,
        name=req.name.strip(),
        base_strategy_name=req.base_strategy_name,
        custom_params=json.dumps(req.custom_params),
        backtest_history_id=req.backtest_history_id,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)

    logger.info("User %d created custom strategy %d: %s", current_user.id, strategy.id, strategy.name)
    return schemas.UserStrategyResponse(
        id=strategy.id,
        name=strategy.name,
        base_strategy_name=strategy.base_strategy_name,
        custom_params=json.loads(strategy.custom_params),
        backtest_history_id=strategy.backtest_history_id,
        created_at=strategy.created_at,
    )


@router.post("/from-backtest/{history_id}", response_model=schemas.UserStrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy_from_backtest(
    history_id: int,
    name: str = Query(..., min_length=1, max_length=50),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트 결과에서 커스텀 전략 생성"""
    history = db.query(models.BacktestHistory).filter(
        models.BacktestHistory.id == history_id,
        models.BacktestHistory.user_id == current_user.id,
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="백테스트 기록을 찾을 수 없습니다.")

    if history.status != "completed":
        raise HTTPException(status_code=400, detail="완료된 백테스트만 전략으로 저장할 수 있습니다.")

    custom_params = safe_json_loads(history.custom_params, {})

    req = schemas.UserStrategyCreate(
        name=name.strip(),
        base_strategy_name=history.strategy_name,
        custom_params=custom_params,
        backtest_history_id=history_id,
    )
    return create_user_strategy(req, current_user, db)


@router.get("/", response_model=list[schemas.UserStrategyResponse])
def list_user_strategies(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """내 커스텀 전략 목록"""
    strategies = db.query(models.UserStrategy).filter(
        models.UserStrategy.user_id == current_user.id,
        models.UserStrategy.is_deleted == False,
    ).order_by(models.UserStrategy.created_at.desc()).all()

    return [
        schemas.UserStrategyResponse(
            id=s.id,
            name=s.name,
            base_strategy_name=s.base_strategy_name,
            custom_params=safe_json_loads(s.custom_params, {}),
            backtest_history_id=s.backtest_history_id,
            created_at=s.created_at,
        )
        for s in strategies
    ]


@router.delete("/{strategy_id}")
def delete_user_strategy(
    strategy_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """커스텀 전략 삭제 (soft-delete)"""
    strategy = db.query(models.UserStrategy).filter(
        models.UserStrategy.id == strategy_id,
        models.UserStrategy.user_id == current_user.id,
        models.UserStrategy.is_deleted == False,
    ).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")

    strategy.is_deleted = True
    db.commit()

    logger.info("User %d deleted custom strategy %d", current_user.id, strategy_id)
    return {"status": "success", "message": "전략이 삭제되었습니다."}
