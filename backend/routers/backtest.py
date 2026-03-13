import logging
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models, schemas
from dependencies import get_db, get_current_user
from core.vector_backtester import VectorBacktester, backtest_tasks
import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _save_backtest_result(task_id: str, task_info: dict):
    """백테스트 완료 시 결과를 DB에 저장 (백그라운드 스레드에서 호출)"""
    db = database.SessionLocal()
    try:
        history_id = task_info.get("history_id")
        if not history_id:
            return

        history = db.query(models.BacktestHistory).filter(
            models.BacktestHistory.id == history_id
        ).first()
        if not history:
            return

        if task_info["status"] == "completed" and task_info.get("result"):
            result = task_info["result"]
            # commission_rate를 result_data JSON에 포함하여 저장
            if task_info.get("commission_rate") is not None:
                result["commission_rate"] = task_info["commission_rate"]
            history.status = "completed"
            history.final_capital = result.get("final_capital")
            history.total_trades = result.get("total_trades")
            history.result_data = json.dumps(result)
        elif task_info["status"] == "failed":
            history.status = "failed"

        db.commit()
        logger.info("Backtest history %d saved (status=%s)", history_id, history.status)
    except Exception as e:
        db.rollback()
        logger.error("Failed to save backtest history: %s", e)
    finally:
        db.close()


def _start_backtest(
    symbols: list[str],
    is_portfolio: bool,
    strategy_name: str,
    timeframe: str,
    limit: int | None,
    initial_capital: float,
    start_date: str | None,
    end_date: str | None,
    commission_rate: float,
    user_id: int,
    db: Session,
) -> dict:
    """백테스트 태스크 생성 + DB 기록의 공통 로직."""
    tester = VectorBacktester(strategy_name=strategy_name)
    task_id = tester.start_async_backtest(
        symbols=symbols,
        is_portfolio=is_portfolio,
        timeframe=timeframe,
        limit=limit,
        initial_capital=initial_capital,
        start_date=start_date,
        end_date=end_date,
        fees=commission_rate,
    )
    backtest_tasks[task_id]["user_id"] = user_id
    backtest_tasks[task_id]["commission_rate"] = commission_rate

    history = models.BacktestHistory(
        user_id=user_id,
        symbols=json.dumps(symbols),
        timeframe=timeframe,
        strategy_name=strategy_name,
        initial_capital=initial_capital,
        status="running",
        start_date=start_date,
        end_date=end_date,
        commission_rate=commission_rate,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    backtest_tasks[task_id]["history_id"] = history.id

    return {"status": "running", "task_id": task_id}


@router.post("/", response_model=schemas.BacktestResponse)
def run_backtest(req: schemas.BacktestRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _start_backtest(
            symbols=[req.symbol], is_portfolio=False,
            strategy_name=req.strategy_name, timeframe=req.timeframe,
            limit=req.limit, initial_capital=req.initial_capital,
            start_date=req.start_date, end_date=req.end_date,
            commission_rate=req.commission_rate, user_id=current_user.id, db=db,
        )
    except Exception as e:
        logger.error("Backtest startup error: %s", e)
        raise HTTPException(status_code=500, detail="Backtest failed to start")


@router.post("/portfolio", response_model=schemas.BacktestResponse)
def run_portfolio_backtest(req: schemas.PortfolioBacktestRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _start_backtest(
            symbols=req.symbols, is_portfolio=True,
            strategy_name=req.strategy_name, timeframe=req.timeframe,
            limit=req.limit, initial_capital=req.initial_capital,
            start_date=req.start_date, end_date=req.end_date,
            commission_rate=req.commission_rate, user_id=current_user.id, db=db,
        )
    except Exception as e:
        logger.error("Portfolio Backtest startup error: %s", e)
        raise HTTPException(status_code=500, detail="Backtest failed to start")


@router.get("/status/{task_id}", response_model=schemas.BacktestTaskResponse)
def get_backtest_status(task_id: str, current_user: models.User = Depends(get_current_user)):
    if task_id not in backtest_tasks:
        raise HTTPException(status_code=404, detail="Backtest task not found")

    task_info = backtest_tasks[task_id]

    if task_info.get("user_id") and task_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this backtest")

    # 완료/실패 시 DB에 결과 저장
    if task_info["status"] in ("completed", "failed") and not task_info.get("_saved"):
        _save_backtest_result(task_id, task_info)
        task_info["_saved"] = True

    return {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info["progress"],
        "message": task_info["message"],
        "result": task_info["result"]
    }


# -------- 백테스트 기록 조회 --------

@router.get("/history", response_model=List[schemas.BacktestHistoryResponse])
def get_backtest_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """내 백테스트 기록 목록 조회"""
    histories = (
        db.query(models.BacktestHistory)
        .filter(models.BacktestHistory.user_id == current_user.id)
        .order_by(models.BacktestHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    results = []
    for h in histories:
        results.append(schemas.BacktestHistoryResponse(
            id=h.id,
            title=h.title,
            symbols=json.loads(h.symbols) if h.symbols else [],
            timeframe=h.timeframe,
            strategy_name=h.strategy_name,
            initial_capital=h.initial_capital,
            final_capital=h.final_capital,
            total_trades=h.total_trades,
            status=h.status,
            start_date=h.start_date,
            end_date=h.end_date,
            commission_rate=h.commission_rate,
            created_at=h.created_at,
        ))
    return results


@router.get("/history/{history_id}", response_model=schemas.BacktestHistoryDetailResponse)
def get_backtest_history_detail(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트 기록 상세 조회 (전체 결과 포함)"""
    history = db.query(models.BacktestHistory).filter(
        models.BacktestHistory.id == history_id,
        models.BacktestHistory.user_id == current_user.id,
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="백테스트 기록을 찾을 수 없습니다.")

    return schemas.BacktestHistoryDetailResponse(
        id=history.id,
        title=history.title,
        symbols=json.loads(history.symbols) if history.symbols else [],
        timeframe=history.timeframe,
        strategy_name=history.strategy_name,
        initial_capital=history.initial_capital,
        final_capital=history.final_capital,
        total_trades=history.total_trades,
        status=history.status,
        start_date=history.start_date,
        end_date=history.end_date,
        commission_rate=history.commission_rate,
        created_at=history.created_at,
        result_data=json.loads(history.result_data) if history.result_data else None,
    )


@router.patch("/history/{history_id}")
def update_backtest_history(
    history_id: int,
    update: schemas.BacktestHistoryUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트 기록 제목 수정"""
    history = db.query(models.BacktestHistory).filter(
        models.BacktestHistory.id == history_id,
        models.BacktestHistory.user_id == current_user.id,
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="백테스트 기록을 찾을 수 없습니다.")

    if update.title is not None:
        history.title = update.title

    db.commit()
    db.refresh(history)
    logger.info("User %d updated backtest history %d title", current_user.id, history_id)
    return {"status": "success", "message": "백테스트 기록이 수정되었습니다."}


@router.delete("/history/{history_id}")
def delete_backtest_history(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트 기록 삭제"""
    history = db.query(models.BacktestHistory).filter(
        models.BacktestHistory.id == history_id,
        models.BacktestHistory.user_id == current_user.id,
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="백테스트 기록을 찾을 수 없습니다.")

    db.delete(history)
    db.commit()
    logger.info("User %d deleted backtest history %d", current_user.id, history_id)
    return {"status": "success", "message": f"백테스트 기록 {history_id}이 삭제되었습니다."}


@router.post("/history/{history_id}/share", response_model=schemas.PostResponse)
def share_backtest_to_community(
    history_id: int,
    title: str = Query(..., min_length=1, max_length=100),
    content: str = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """백테스트 기록을 커뮤니티에 공유"""
    history = db.query(models.BacktestHistory).filter(
        models.BacktestHistory.id == history_id,
        models.BacktestHistory.user_id == current_user.id,
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="백테스트 기록을 찾을 수 없습니다.")

    if history.status != "completed":
        raise HTTPException(status_code=400, detail="완료된 백테스트만 공유할 수 있습니다.")

    # 공유용 요약 데이터 생성
    backtest_summary = {
        "strategy_name": history.strategy_name,
        "symbols": json.loads(history.symbols) if history.symbols else [],
        "timeframe": history.timeframe,
        "initial_capital": history.initial_capital,
        "final_capital": history.final_capital,
        "total_trades": history.total_trades,
        "start_date": history.start_date,
        "end_date": history.end_date,
        "commission_rate": history.commission_rate,
    }

    post = models.CommunityPost(
        user_id=current_user.id,
        post_type="backtest_share",
        title=title,
        content=content,
        backtest_data=json.dumps(backtest_summary),
        strategy_name=history.strategy_name,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    logger.info("User %d shared backtest %d as post %d", current_user.id, history_id, post.id)

    # PostResponse 형태로 반환
    return schemas.PostResponse(
        id=post.id,
        user_id=post.user_id,
        author_nickname=current_user.nickname,
        post_type=post.post_type,
        title=post.title,
        content=post.content,
        backtest_data=backtest_summary,
        performance_data=None,
        strategy_name=post.strategy_name,
        rating=None,
        like_count=0,
        comment_count=0,
        is_liked=False,
        created_at=post.created_at,
    )
