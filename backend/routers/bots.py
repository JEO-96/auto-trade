import asyncio
import logging
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

import bot_manager
import models
import schemas
from constants import (
    MAX_BOTS_PER_USER,
    MAX_BOTS_PER_REGULAR_USER,
    MAX_LIVE_BOTS_PER_USER,
    SYMBOL_PATTERN,
    VALID_TIMEFRAMES,
)
from crypto_utils import fetch_exchange_balance
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
    """새 봇 설정 생성"""
    # 사용자당 봇 수 제한 (일반 사용자 1개, 관리자 5개)
    bot_count = db.query(models.BotConfig).filter(
        models.BotConfig.user_id == current_user.id
    ).count()
    max_bots = MAX_BOTS_PER_USER if current_user.is_admin else MAX_BOTS_PER_REGULAR_USER
    if bot_count >= max_bots:
        if current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"최대 {max_bots}개까지 봇을 생성할 수 있습니다.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="모의투자 봇은 1개만 운영할 수 있습니다. 기존 봇을 삭제 후 새로 만들어주세요.",
        )

    # 실매매 봇: 법률 검토 완료 전까지 관리자만 허용
    if not req.paper_trading_mode:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="실매매 기능은 현재 준비 중입니다. 모의투자 모드를 이용해주세요.",
            )
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

    if req.allocated_capital < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Allocated capital must be non-negative.",
        )

    # 커스텀 전략 검증
    custom_strategy_id = req.custom_strategy_id
    if custom_strategy_id:
        user_strategy = db.query(models.UserStrategy).filter(
            models.UserStrategy.id == custom_strategy_id,
            models.UserStrategy.user_id == current_user.id,
            models.UserStrategy.is_deleted == False,
        ).first()
        if not user_strategy:
            raise HTTPException(status_code=404, detail="커스텀 전략을 찾을 수 없습니다.")

    bot = models.BotConfig(
        user_id=current_user.id,
        symbol=req.symbol,
        timeframe=req.timeframe,
        exchange_name=req.exchange_name,
        strategy_name=req.strategy_name,
        paper_trading_mode=req.paper_trading_mode,
        allocated_capital=req.allocated_capital,
        custom_strategy_id=custom_strategy_id,
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

    # 모의투자 → 실매매로 변경 시: 관리자만 허용 + 기존 실매매 봇 수 체크
    if "paper_trading_mode" in update_data and update_data["paper_trading_mode"] is False:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="실매매 기능은 현재 준비 중입니다. 모의투자 모드를 이용해주세요.",
            )
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

    # 실매매 봇: 관리자만 시작 허용
    if not bot.paper_trading_mode and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="실매매 기능은 현재 준비 중입니다. 모의투자 모드를 이용해주세요.",
        )

    # 실매매 봇 검증: 운용자본 vs 거래소 KRW 잔고
    if not bot.paper_trading_mode:
        bot_exchange = getattr(bot, 'exchange_name', 'upbit') or 'upbit'
        exchange_label = bot_exchange.upper()

        # 거래소 KRW 잔고 조회 → allocated_capital 초과 불가
        balance = fetch_exchange_balance(current_user.id, bot_exchange, db)
        krw_free = float(balance.get("KRW", {}).get("free", 0))

        if bot.allocated_capital > krw_free:
            # 봇 심볼에 해당하는 코인 보유 중이면 허용 (봇이 기존 포지션을 감지하여 관리)
            bot_symbols = parse_symbols(bot.symbol)
            has_coin_holdings = any(
                float(balance.get(sym.split('/')[0], {}).get('free', 0) or 0) > 0
                for sym in bot_symbols
            )
            if not has_coin_holdings:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"운용 자본({bot.allocated_capital:,.0f}원)이 {exchange_label} 보유 현금({krw_free:,.0f}원)보다 큽니다. 금액을 줄여주세요.",
                )

    task = asyncio.create_task(bot_manager.run_bot_loop(bot_id))
    bot_manager.active_bots[bot_id] = task

    return {"status": "success", "message": f"Bot {bot_id} started."}

@router.post("/stop/{bot_id}")
async def stop_bot(bot_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = _get_user_bot(bot_id, current_user.id, db)

    task = bot_manager.active_bots.get(bot_id)
    if task is not None and not task.done():
        task.cancel()
        # cancel 후 task의 CancelledError 핸들러에서 포지션 매도 + finally 정리 완료 대기
        try:
            await task
        except asyncio.CancelledError:
            pass
        # CancelledError 핸들러가 포지션 매도 후 DB를 정리함
        bot_manager.clear_positions_from_db(bot_id)
        return {"status": "success", "message": f"Bot {bot_id} stopped. 보유 포지션이 자동 청산되었습니다."}
    # 메모리에 없지만 DB에 active로 남아있을 수 있음
    bot_manager.set_bot_active(bot_id, False)
    bot_manager.clear_positions_from_db(bot_id)
    return {"status": "error", "message": f"Bot was not running."}

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

@router.get("/performance/{bot_id}", response_model=schemas.BotPerformanceResponse)
def get_bot_performance(
    bot_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """봇 성과 통계: 총 PnL, 승률, 최대 드로다운, 일별/주별 PnL"""
    _get_user_bot(bot_id, current_user.id, db)

    # SELL 거래만 PnL이 있으므로 전체 조회 후 필터
    logs = (
        db.query(models.TradeLog)
        .filter(models.TradeLog.bot_id == bot_id)
        .order_by(models.TradeLog.timestamp.asc())
        .all()
    )

    # PnL이 있는 거래 (SELL)만 통계 대상
    pnl_trades = [log for log in logs if log.pnl is not None]
    total_trades = len(pnl_trades)
    total_pnl = sum(t.pnl for t in pnl_trades)
    win_count = sum(1 for t in pnl_trades if t.pnl > 0)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

    # 일별 PnL 집계
    daily_map: dict[str, float] = defaultdict(float)
    for t in pnl_trades:
        try:
            date_str = datetime.fromisoformat(t.timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            date_str = t.timestamp[:10] if t.timestamp and len(t.timestamp) >= 10 else "unknown"
        daily_map[date_str] += t.pnl

    cumulative = 0.0
    daily_pnl = []
    for date_str in sorted(daily_map.keys()):
        cumulative += daily_map[date_str]
        daily_pnl.append(schemas.DailyPnl(
            date=date_str,
            pnl=round(daily_map[date_str], 2),
            cumulative_pnl=round(cumulative, 2),
        ))

    # 주별 PnL 집계 (ISO week)
    weekly_map: dict[str, float] = defaultdict(float)
    for t in pnl_trades:
        try:
            dt = datetime.fromisoformat(t.timestamp.replace("Z", "+00:00"))
            iso = dt.isocalendar()
            week_str = f"{iso[0]}-W{iso[1]:02d}"
        except (ValueError, AttributeError):
            week_str = "unknown"
        weekly_map[week_str] += t.pnl

    weekly_pnl = [
        schemas.WeeklyPnl(week=w, pnl=round(weekly_map[w], 2))
        for w in sorted(weekly_map.keys())
    ]

    # 최대 드로다운 (누적 PnL 기준, %)
    max_drawdown = 0.0
    if daily_pnl:
        peak = daily_pnl[0].cumulative_pnl
        for dp in daily_pnl:
            if dp.cumulative_pnl > peak:
                peak = dp.cumulative_pnl
            if peak > 0:
                dd = (dp.cumulative_pnl - peak) / peak * 100
                if dd < max_drawdown:
                    max_drawdown = dd

    return schemas.BotPerformanceResponse(
        bot_id=bot_id,
        total_pnl=round(total_pnl, 2),
        total_trades=total_trades,
        win_rate=round(win_rate, 1),
        max_drawdown=round(max_drawdown, 1),
        daily_pnl=daily_pnl,
        weekly_pnl=weekly_pnl,
    )


@router.get("/list", response_model=list[schemas.BotConfigResponse])
def list_user_bots(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    bots = db.query(models.BotConfig).filter(models.BotConfig.user_id == current_user.id).all()
    results = []
    for b in bots:
        data = schemas.BotConfigResponse.model_validate(b)
        # 커스텀 전략 이름 조회
        if b.custom_strategy_id:
            cs = db.query(models.UserStrategy).filter(
                models.UserStrategy.id == b.custom_strategy_id,
                models.UserStrategy.is_deleted == False,
            ).first()
            if cs:
                data.custom_strategy_name = cs.name
        results.append(data)
    return results
