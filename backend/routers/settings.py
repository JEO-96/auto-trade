import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models, schemas
from dependencies import get_db, get_current_user, get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

# 기본값: 전략별 허용 타임프레임 (설정이 없을 때 폴백)
DEFAULT_STRATEGY_TIMEFRAMES: dict[str, list[str]] = {
    "james_basic": ["1h", "4h", "1d"],
    "james_pro_stable": ["1h", "4h"],
    "james_pro_aggressive": ["1h", "4h"],
    "james_pro_elite": ["4h", "1d"],
    "steady_compounder": ["4h"],
}

SETTINGS_KEY = "backtest_strategy_timeframes"


@router.get("/backtest", response_model=schemas.BacktestSettingsResponse)
def get_backtest_settings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트에서 허용된 전략별 타임프레임 조회 (로그인 사용자)"""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == SETTINGS_KEY
    ).first()

    strategy_timeframes = (
        json.loads(setting.value)
        if setting
        else DEFAULT_STRATEGY_TIMEFRAMES
    )

    return schemas.BacktestSettingsResponse(
        strategy_timeframes=strategy_timeframes,
    )


@router.put("/backtest", response_model=schemas.BacktestSettingsResponse)
def update_backtest_settings(
    update: schemas.BacktestSettingsUpdate,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """백테스트 허용 전략별 타임프레임 수정 (관리자 전용)"""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == SETTINGS_KEY
    ).first()

    if setting:
        setting.value = json.dumps(update.strategy_timeframes)
    else:
        setting = models.SystemSettings(
            key=SETTINGS_KEY,
            value=json.dumps(update.strategy_timeframes),
        )
        db.add(setting)

    db.commit()
    logger.info("Admin %d updated backtest strategy-timeframe settings", admin.id)

    return schemas.BacktestSettingsResponse(
        strategy_timeframes=update.strategy_timeframes,
    )
