import asyncio
import logging

import ccxt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

import bot_manager
import credit_service
import models
import schemas
from constants import (
    MAX_BOTS_PER_USER,
    MAX_LIVE_BOTS_PER_USER,
    SYMBOL_PATTERN,
    VALID_TIMEFRAMES,
)
from crypto_utils import decrypt_key
from dependencies import get_db, get_current_user
from utils import parse_symbols, mask_nickname

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bot", tags=["bots"])


@router.get("/active", response_model=schemas.ActiveBotListResponse)
def get_active_bots(db: Session = Depends(get_db)):
    """현재 실제 실행 중인 봇 목록 (공개, 인증 불필요)"""
    running_ids = [
        bid for bid, task in list(bot_manager.active_bots.items())
        if not task.done()
    ]
    if not running_ids:
        return schemas.ActiveBotListResponse(bots=[], total=0)

    bots = (
        db.query(models.BotConfig)
        .options(joinedload(models.BotConfig.owner))
        .filter(models.BotConfig.id.in_(running_ids))
        .all()
    )

    result = []
    for bot in bots:
        raw_name = (bot.owner.nickname or bot.owner.email.split('@')[0]) if bot.owner else None
        result.append(schemas.ActiveBotPublic(
            nickname=mask_nickname(raw_name),
            symbol=bot.symbol,
            timeframe=bot.timeframe,
            strategy_name=bot.strategy_name,
            paper_trading_mode=bot.paper_trading_mode,
        ))

    return schemas.ActiveBotListResponse(bots=result, total=len(result))


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
    """봇이 현재 실행 중인지 확인 (TOCTOU-safe)"""
    task = bot_manager.active_bots.get(bot_id)
    return task is not None and not task.done()


def _validate_symbol(symbol: str) -> None:
    """심볼 형식 검증 (예: BTC/KRW 또는 BTC/KRW,ETH/KRW)"""
    symbols = parse_symbols(symbol)
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
    """타임프레임 검증 (constants 기반)"""
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
    bot = _get_user_bot(bot_id, current_user.id, db)

    if _is_bot_running(bot_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bot already running.")

    # 실매매 봇 검증: 크레딧 + 운용자본 vs 업비트 KRW 잔고
    if not bot.paper_trading_mode:
        if not credit_service.check_sufficient_credits(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="크레딧이 부족합니다. 크레딧을 충전한 후 다시 시도해주세요.",
            )

        # 업비트 KRW 잔고 조회 → allocated_capital 초과 불가
        exchange_key = db.query(models.ExchangeKey).filter(
            models.ExchangeKey.user_id == current_user.id,
            models.ExchangeKey.exchange_name == "upbit",
        ).first()
        if not exchange_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="등록된 Upbit API 키가 없습니다. 먼저 API 키를 등록해주세요.",
            )
        try:
            api_key = decrypt_key(exchange_key.api_key_encrypted)
            api_secret = decrypt_key(exchange_key.api_secret_encrypted)
            exchange = ccxt.upbit({
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            })
            balance = exchange.fetch_balance()
            krw_free = float(balance.get("KRW", {}).get("free", 0))
        except Exception as e:
            logger.error("Failed to fetch Upbit balance for user %d: %s", current_user.id, e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="업비트 잔고 조회에 실패했습니다. 잠시 후 다시 시도해주세요.",
            )

        if bot.allocated_capital > krw_free:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"운용 자본({bot.allocated_capital:,.0f}원)이 업비트 보유 현금({krw_free:,.0f}원)보다 큽니다. 금액을 줄여주세요.",
            )

    task = asyncio.create_task(bot_manager.run_bot_loop(bot_id))
    bot_manager.active_bots[bot_id] = task

    return {"status": "success", "message": f"Bot {bot_id} started."}

@router.post("/stop/{bot_id}")
async def stop_bot(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = _get_user_bot(bot_id, current_user.id, db)

    # 실매매 봇의 보유 포지션 확인 (소유권 확인된 bot_id만 조회)
    has_positions = db.query(models.ActivePosition).filter(
        models.ActivePosition.bot_id == bot_id
    ).count() > 0
    warning = ""
    if not bot.paper_trading_mode and has_positions:
        warning = " 주의: 실매매 포지션이 있습니다. 거래소에서 보유 중인 코인을 직접 확인해주세요."

    task = bot_manager.active_bots.get(bot_id)
    if task is not None and not task.done():
        task.cancel()
        # cancel 후 task의 finally 블록이 완료될 때까지 대기
        # (finally에서 active_bots.pop + set_bot_active(False) 실행됨)
        try:
            await task
        except asyncio.CancelledError:
            pass
        # finally 블록이 포지션을 DB에 저장한 후 정리
        bot_manager.clear_positions_from_db(bot_id)
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

@router.get("/list", response_model=list[schemas.BotConfigResponse])
def list_user_bots(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.BotConfig).filter(models.BotConfig.user_id == current_user.id).all()
