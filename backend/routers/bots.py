import re
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import asyncio
import models, schemas, bot_manager
from dependencies import get_db, get_current_user
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bot", tags=["bots"])

# 사용자당 최대 봇 수
MAX_BOTS_PER_USER = 5
# 실매매 봇은 사용자당 최대 1개
MAX_LIVE_BOTS_PER_USER = 1

# 심볼 형식 검증 (예: BTC/KRW, ETH/USDT)
SYMBOL_PATTERN = re.compile(r'^[A-Z0-9]{2,10}/[A-Z]{3,5}$')

# 허용되는 타임프레임
VALID_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"}


def _get_user_bot(bot_id: int, user_id: int, db: Session) -> models.BotConfig:
    """Fetch a bot config owned by the given user, or raise 404."""
    bot = db.query(models.BotConfig).filter(
        models.BotConfig.id == bot_id,
        models.BotConfig.user_id == user_id,
    ).first()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot configuration not found.")
    return bot


def _is_bot_running(bot_id: int) -> bool:
    """봇이 현재 실행 중인지 확인"""
    return bot_id in bot_manager.active_bots and not bot_manager.active_bots[bot_id].done()


def _validate_symbol(symbol: str) -> None:
    """심볼 형식 검증 (예: BTC/KRW 또는 BTC/KRW,ETH/KRW)"""
    symbols = [s.strip() for s in symbol.split(',') if s.strip()]
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one symbol is required.",
        )
    for s in symbols:
        if not SYMBOL_PATTERN.match(s):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid symbol format: '{s}'. Expected format: 'BTC/KRW'.",
            )


def _validate_timeframe(timeframe: str) -> None:
    """타임프레임 검증"""
    if timeframe not in VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid timeframe: '{timeframe}'. Allowed: {sorted(VALID_TIMEFRAMES)}",
        )


# -------- CRUD 엔드포인트 --------

@router.post("/", response_model=schemas.BotConfigResponse, status_code=status.HTTP_201_CREATED)
def create_bot(
    req: schemas.BotConfigCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """새 봇 설정 생성 (사용자당 최대 5개)"""
    # 사용자당 봇 수 제한
    bot_count = db.query(models.BotConfig).filter(
        models.BotConfig.user_id == current_user.id
    ).count()
    if bot_count >= MAX_BOTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BOTS_PER_USER} bots allowed per user.",
        )

    # 실매매 봇 개수 제한 (사용자당 1개)
    if not req.paper_trading_mode:
        live_bot_count = db.query(models.BotConfig).filter(
            models.BotConfig.user_id == current_user.id,
            models.BotConfig.paper_trading_mode == False,
        ).count()
        if live_bot_count >= MAX_LIVE_BOTS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"실매매 봇은 최대 {MAX_LIVE_BOTS_PER_USER}개까지만 생성할 수 있습니다. 모의투자 봇은 무제한입니다.",
            )

    # 입력값 검증
    _validate_symbol(req.symbol)
    _validate_timeframe(req.timeframe)

    if req.allocated_capital <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Allocated capital must be positive.",
        )

    bot = models.BotConfig(
        user_id=current_user.id,
        symbol=req.symbol,
        timeframe=req.timeframe,
        strategy_name=req.strategy_name,
        paper_trading_mode=req.paper_trading_mode,
        allocated_capital=req.allocated_capital,
        rsi_period=req.rsi_period,
        macd_fast=req.macd_fast,
        macd_slow=req.macd_slow,
        volume_ma_period=req.volume_ma_period,
        is_active=False,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)

    logger.info("User %d created bot %d (symbol=%s)", current_user.id, bot.id, bot.symbol)
    return bot


@router.put("/{bot_id}", response_model=schemas.BotConfigResponse)
def update_bot(
    bot_id: int,
    req: schemas.BotConfigUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """봇 설정 수정 (정지 상태에서만 가능)"""
    bot = _get_user_bot(bot_id, current_user.id, db)

    if _is_bot_running(bot_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update a running bot. Stop it first.",
        )

    # 변경 요청된 필드만 업데이트
    update_data = req.model_dump(exclude_unset=True)

    if "symbol" in update_data:
        _validate_symbol(update_data["symbol"])

    if "timeframe" in update_data:
        _validate_timeframe(update_data["timeframe"])

    if "allocated_capital" in update_data and update_data["allocated_capital"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Allocated capital must be positive.",
        )

    # 모의투자 → 실매매로 변경 시, 기존 실매매 봇 수 체크
    if "paper_trading_mode" in update_data and update_data["paper_trading_mode"] is False:
        if bot.paper_trading_mode:  # 현재 모의투자인 봇을 실매매로 바꾸려는 경우만
            live_bot_count = db.query(models.BotConfig).filter(
                models.BotConfig.user_id == current_user.id,
                models.BotConfig.paper_trading_mode == False,
            ).count()
            if live_bot_count >= MAX_LIVE_BOTS_PER_USER:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"실매매 봇은 최대 {MAX_LIVE_BOTS_PER_USER}개까지만 허용됩니다. 기존 실매매 봇을 모의투자로 전환하거나 삭제 후 다시 시도하세요.",
                )

    for field, value in update_data.items():
        setattr(bot, field, value)

    db.commit()
    db.refresh(bot)

    logger.info("User %d updated bot %d", current_user.id, bot.id)
    return bot


@router.delete("/{bot_id}")
def delete_bot(
    bot_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """봇 설정 삭제 (정지 상태에서만 가능)"""
    bot = _get_user_bot(bot_id, current_user.id, db)

    if _is_bot_running(bot_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a running bot. Stop it first.",
        )

    # 관련 데이터 함께 삭제
    db.query(models.ActivePosition).filter(models.ActivePosition.bot_id == bot_id).delete()
    db.query(models.TradeLog).filter(models.TradeLog.bot_id == bot_id).delete()
    db.delete(bot)
    db.commit()

    logger.info("User %d deleted bot %d", current_user.id, bot.id)
    return {"status": "success", "message": f"Bot {bot_id} deleted."}


# -------- 봇 제어 엔드포인트 --------

@router.post("/start/{bot_id}")
async def start_bot(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_user_bot(bot_id, current_user.id, db)

    if _is_bot_running(bot_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bot already running.")

    task = asyncio.create_task(bot_manager.run_bot_loop(bot_id))
    bot_manager.active_bots[bot_id] = task

    return {"status": "success", "message": f"Bot {bot_id} started."}

@router.post("/stop/{bot_id}")
async def stop_bot(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_user_bot(bot_id, current_user.id, db)

    # 실매매 봇의 보유 포지션 확인
    bot = _get_user_bot(bot_id, current_user.id, db)
    has_positions = db.query(models.ActivePosition).filter(
        models.ActivePosition.bot_id == bot_id
    ).count() > 0
    warning = ""
    if not bot.paper_trading_mode and has_positions:
        warning = " 주의: 실매매 포지션이 있습니다. 거래소에서 보유 중인 코인을 직접 확인해주세요."

    if bot_id in bot_manager.active_bots:
        task = bot_manager.active_bots.pop(bot_id)
        task.cancel()
        # cancel 후 task 완료 대기 (포지션 저장이 끝날 때까지)
        try:
            await task
        except asyncio.CancelledError:
            pass
        bot_manager.clear_positions_from_db(bot_id)
        bot_manager.set_bot_active(bot_id, False)
        return {"status": "success", "message": f"Bot {bot_id} stopped.{warning}"}
    # 메모리에 없지만 DB에 active로 남아있을 수 있음
    bot_manager.set_bot_active(bot_id, False)
    bot_manager.clear_positions_from_db(bot_id)
    return {"status": "error", "message": f"Bot was not running.{warning}"}

@router.get("/status/{bot_id}")
def status_bot(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_user_bot(bot_id, current_user.id, db)

    bot_status = bot_manager.get_bot_status(bot_id)
    return {"status": "success", "bot_status": bot_status}

@router.get("/logs/{bot_id}", response_model=list[schemas.TradeLogResponse])
def get_bot_trade_logs(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_user_bot(bot_id, current_user.id, db)

    logs = db.query(models.TradeLog).filter(
        models.TradeLog.bot_id == bot_id
    ).order_by(models.TradeLog.id.desc()).limit(100).all()
    return logs

@router.get("/list", response_model=List[schemas.BotConfigResponse])
def list_user_bots(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.BotConfig).filter(models.BotConfig.user_id == current_user.id).all()
