import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models, schemas
from dependencies import get_db, get_current_user, get_current_user_optional, get_admin_user
from constants import STRATEGY_DEFINITIONS, BACKTEST_STRATEGY_ALIASES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

# 기본값: 전략별 허용 타임프레임 (설정이 없을 때 폴백)
DEFAULT_STRATEGY_TIMEFRAMES: dict[str, list[str]] = {
    "james_basic": ["1h", "4h", "1d"],
    "james_pro_stable": ["1h", "4h"],
    "james_pro_aggressive": ["1h", "4h"],
    "james_pro_elite": ["4h", "1d"],
    "steady_compounder": ["4h"],
    # Timeframe-optimized (각 전략의 최적 타임프레임 고정)
    "momentum_basic_1d": ["1d"],
    "momentum_stable_1h": ["1h"],
    "momentum_stable_1d": ["1d"],
    "momentum_aggressive_1h": ["1h"],
    "momentum_aggressive_4h": ["4h"],
    "momentum_aggressive_1d": ["1d"],
    "momentum_elite_1d": ["1d"],
    "steady_compounder_4h": ["4h"],
}

SETTINGS_KEY = "backtest_strategy_timeframes"
VISIBILITY_KEY = "strategy_visibility"


def _get_visibility_overrides(db: Session) -> dict[str, bool]:
    """DB에 저장된 전략 공개 설정 조회. 없으면 빈 dict."""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == VISIBILITY_KEY
    ).first()
    if setting:
        return json.loads(setting.value)
    return {}


def _build_strategy_list(db: Session, is_admin: bool) -> list[dict]:
    """사용자 권한에 따라 전략 목록 생성."""
    overrides = _get_visibility_overrides(db)

    result = []
    for s in STRATEGY_DEFINITIONS:
        is_public = overrides.get(s["value"], s["is_public"])
        if is_admin or is_public:
            result.append({
                "value": s["value"],
                "label": s["label"],
                "is_public": is_public,
            })
    return result


@router.get("/strategies")
def get_strategies(
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    사용 가능한 전략 목록 반환.
    - 일반 사용자: 공개 전략만
    - 관리자: 전체 전략 (is_public 표시 포함)
    """
    is_admin = current_user.is_admin if current_user else False
    strategies = _build_strategy_list(db, is_admin)

    # 백테스트 별칭도 포함 (공개된 전략에 매핑된 것만)
    public_values = {s["value"] for s in strategies}
    aliases = []
    for alias in BACKTEST_STRATEGY_ALIASES:
        if is_admin or alias["maps_to"] in public_values:
            aliases.append({"value": alias["value"], "label": alias["label"]})

    return {
        "strategies": strategies,
        "backtest_aliases": aliases,
    }


@router.put("/strategies/visibility")
def update_strategy_visibility(
    update: schemas.StrategyVisibilityUpdate,
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """전략 공개/비공개 설정 변경 (관리자 전용)"""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == VISIBILITY_KEY
    ).first()

    # 기존 설정에 병합
    current = json.loads(setting.value) if setting else {}
    current.update(update.visibility)

    if setting:
        setting.value = json.dumps(current)
    else:
        setting = models.SystemSettings(
            key=VISIBILITY_KEY,
            value=json.dumps(current),
        )
        db.add(setting)

    db.commit()
    logger.info("Admin %d updated strategy visibility: %s", admin.id, update.visibility)

    return {"strategies": _build_strategy_list(db, is_admin=True)}


@router.get("/backtest", response_model=schemas.BacktestSettingsResponse)
def get_backtest_settings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트에서 허용된 전략별 타임프레임 조회 (로그인 사용자)"""
    setting = db.query(models.SystemSettings).filter(
        models.SystemSettings.key == SETTINGS_KEY
    ).first()

    # DB 설정이 있으면 로드, 없으면 기본값 사용
    # DB에 없는 새 전략은 기본값에서 병합
    if setting:
        strategy_timeframes = json.loads(setting.value)
        for key, val in DEFAULT_STRATEGY_TIMEFRAMES.items():
            if key not in strategy_timeframes:
                strategy_timeframes[key] = val
    else:
        strategy_timeframes = DEFAULT_STRATEGY_TIMEFRAMES

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
