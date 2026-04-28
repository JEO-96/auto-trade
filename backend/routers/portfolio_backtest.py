"""포트폴리오 백테스트 라우터 — ETF Dual Momentum 등 다자산 전략."""
import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import database
import models
from core.portfolio_backtester import PortfolioBacktester
from core.portfolio_strategy_registry import list_portfolio_strategies
from dependencies import get_current_user, get_db

# task_id → {status, progress, message, result, user_id, request, created_at}
portfolio_tasks: Dict[str, Dict[str, Any]] = {}

# task가 너무 오래 보관되지 않도록 최대 보관 시간(초) — 1시간
_TASK_TTL_SECONDS = 3600


def _purge_old_tasks() -> None:
    """오래된 작업 정리 — 메모리 누수 방지."""
    now = time.time()
    expired = [k for k, v in portfolio_tasks.items()
               if now - v.get("created_at", now) > _TASK_TTL_SECONDS]
    for k in expired:
        portfolio_tasks.pop(k, None)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["portfolio-backtest"])

# 포트폴리오 전략명 prefix (BacktestHistory 테이블 공유, prefix로 구분)
_PORTFOLIO_STRATEGY_PREFIX = "dual_momentum"


class DualMomentumRequest(BaseModel):
    strategy_name: str = Field(default="dual_momentum_etf_v1")
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    initial_capital: float = Field(default=10_000_000)
    commission_rate: float = Field(default=0.001)
    lookback_months: Optional[int] = Field(default=None, ge=1, le=36)
    evaluation_mode: Optional[str] = Field(default=None, description="sequential | best_momentum")
    rebalance_freq: str = Field(default="monthly", description="monthly | quarterly | semiannual")


class PortfolioHistoryItem(BaseModel):
    id: int
    title: Optional[str]
    strategy_name: str
    assets: List[str]
    initial_capital: float
    final_capital: Optional[float]
    total_trades: Optional[int]
    start_date: Optional[str]
    end_date: Optional[str]
    commission_rate: Optional[float]
    status: str
    created_at: str
    custom_params: Optional[dict] = None


class PortfolioHistoryDetail(PortfolioHistoryItem):
    result_data: Optional[dict]


def _save_history(
    db: Session,
    user_id: int,
    req: DualMomentumRequest,
    result: dict,
) -> int:
    """백테스트 결과를 BacktestHistory 테이블에 저장."""
    assets = result.get("assets", [])
    custom = {
        "lookback_months": req.lookback_months,
        "evaluation_mode": req.evaluation_mode,
        "rebalance_freq": req.rebalance_freq,
    }
    history = models.BacktestHistory(
        user_id=user_id,
        title=None,
        symbols=json.dumps(assets),
        timeframe="1d",
        strategy_name=req.strategy_name,
        initial_capital=req.initial_capital,
        final_capital=result.get("final_capital"),
        total_trades=len(result.get("trades", [])),
        result_data=json.dumps(result),
        status="completed",
        start_date=req.start_date,
        end_date=req.end_date,
        commission_rate=req.commission_rate,
        custom_params=json.dumps(custom),
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history.id


_STRATEGY_INFO = {
    "dual_momentum_etf_v1": {
        "label": "듀얼 모멘텀 v1 (KR+US, sequential)",
        "description": "069500/360750 + 153130. 069500 우선 평가 — 운영 기본값.",
        "assets": ["069500", "360750", "153130"],
        "min_data_year": 2020,
    },
    "dual_momentum_etf_v2": {
        "label": "듀얼 모멘텀 v2 (KR+US, Antonacci 정합)",
        "description": "069500/360750 + 153130. 위험자산 중 모멘텀 max 선택.",
        "assets": ["069500", "360750", "153130"],
        "min_data_year": 2020,
    },
    "dual_momentum_etf_kr_v1": {
        "label": "듀얼 모멘텀 KR (069500 + 153130, 장기)",
        "description": "국내 ETF + 채권 2자산. 2002년부터 장기 백테스트 가능.",
        "assets": ["069500", "153130"],
        "min_data_year": 2012,
    },
}


@router.get("/portfolio_strategies")
def list_strategies():
    """사용 가능한 포트폴리오 전략 목록."""
    return [
        {"name": name, **_STRATEGY_INFO.get(name, {"label": name, "description": ""})}
        for name in list_portfolio_strategies()
    ]


def _run_backtest_async(task_id: str, user_id: int, req: DualMomentumRequest) -> None:
    """백그라운드 스레드에서 백테스트 실행."""
    def _set_progress(pct: float, msg: str) -> None:
        info = portfolio_tasks.get(task_id)
        if info is not None:
            info["progress"] = float(pct)
            info["message"] = msg

    db = database.SessionLocal()
    try:
        tester = PortfolioBacktester(
            strategy_name=req.strategy_name,
            commission_rate=req.commission_rate,
            lookback_months=req.lookback_months,
            evaluation_mode=req.evaluation_mode,
            rebalance_freq=req.rebalance_freq,
        )
        result = tester.run(
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            db=db,
            progress_callback=_set_progress,
        )
        # 히스토리 저장 (실패해도 결과는 보존)
        try:
            history_id = _save_history(db, user_id, req, result)
            result["history_id"] = history_id
        except Exception as e:
            logger.warning("Failed to save portfolio backtest history: %s", e)

        info = portfolio_tasks.get(task_id)
        if info is not None:
            info["status"] = "completed"
            info["progress"] = 100.0
            info["message"] = "완료"
            info["result"] = result
            info["completed_at"] = time.time()
    except ValueError as e:
        info = portfolio_tasks.get(task_id)
        if info is not None:
            info["status"] = "failed"
            info["message"] = str(e)
        logger.warning("Dual momentum backtest validation failed: %s", e)
    except Exception as e:
        info = portfolio_tasks.get(task_id)
        if info is not None:
            info["status"] = "failed"
            info["message"] = "Portfolio backtest failed"
        logger.exception("Dual momentum backtest failed: %s", e)
    finally:
        db.close()


@router.post("/dual_momentum/")
def run_dual_momentum_backtest(
    req: DualMomentumRequest,
    current_user: models.User = Depends(get_current_user),
):
    """비동기 시작. task_id 반환 — 클라이언트는 status로 폴링."""
    _purge_old_tasks()
    task_id = str(uuid.uuid4())
    portfolio_tasks[task_id] = {
        "status": "running",
        "progress": 0.0,
        "message": "초기화 중...",
        "result": None,
        "user_id": current_user.id,
        "created_at": time.time(),
    }
    thread = threading.Thread(
        target=_run_backtest_async,
        args=(task_id, current_user.id, req),
        daemon=True,
    )
    thread.start()
    return {"task_id": task_id, "status": "running"}


@router.get("/dual_momentum/status/{task_id}")
def get_dual_momentum_status(
    task_id: str,
    current_user: models.User = Depends(get_current_user),
):
    info = portfolio_tasks.get(task_id)
    if not info:
        raise HTTPException(status_code=404, detail="Task not found")
    if info.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "task_id": task_id,
        "status": info["status"],
        "progress": info["progress"],
        "message": info["message"],
        "result": info["result"],
    }


@router.get("/portfolio_history", response_model=List[PortfolioHistoryItem])
def list_portfolio_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """현재 사용자의 포트폴리오 백테스트 기록 목록."""
    rows = (
        db.query(models.BacktestHistory)
        .filter(
            models.BacktestHistory.user_id == current_user.id,
            models.BacktestHistory.strategy_name.like(f"{_PORTFOLIO_STRATEGY_PREFIX}%"),
        )
        .order_by(models.BacktestHistory.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    out: List[PortfolioHistoryItem] = []
    for r in rows:
        try:
            assets = json.loads(r.symbols) if r.symbols else []
        except (TypeError, ValueError):
            assets = []
        try:
            custom = json.loads(r.custom_params) if r.custom_params else None
        except (TypeError, ValueError):
            custom = None
        out.append(PortfolioHistoryItem(
            id=r.id,
            title=r.title,
            strategy_name=r.strategy_name,
            assets=assets,
            initial_capital=r.initial_capital,
            final_capital=r.final_capital,
            total_trades=r.total_trades,
            start_date=r.start_date,
            end_date=r.end_date,
            commission_rate=r.commission_rate,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else "",
            custom_params=custom,
        ))
    return out


@router.get("/portfolio_history/{history_id}", response_model=PortfolioHistoryDetail)
def get_portfolio_history_detail(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = (
        db.query(models.BacktestHistory)
        .filter(
            models.BacktestHistory.id == history_id,
            models.BacktestHistory.user_id == current_user.id,
            models.BacktestHistory.strategy_name.like(f"{_PORTFOLIO_STRATEGY_PREFIX}%"),
        )
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="History not found")
    try:
        assets = json.loads(r.symbols) if r.symbols else []
    except (TypeError, ValueError):
        assets = []
    try:
        result_data = json.loads(r.result_data) if r.result_data else None
    except (TypeError, ValueError):
        result_data = None
    try:
        custom = json.loads(r.custom_params) if r.custom_params else None
    except (TypeError, ValueError):
        custom = None
    return PortfolioHistoryDetail(
        id=r.id,
        title=r.title,
        strategy_name=r.strategy_name,
        assets=assets,
        initial_capital=r.initial_capital,
        final_capital=r.final_capital,
        total_trades=r.total_trades,
        start_date=r.start_date,
        end_date=r.end_date,
        commission_rate=r.commission_rate,
        status=r.status,
        created_at=r.created_at.isoformat() if r.created_at else "",
        custom_params=custom,
        result_data=result_data,
    )


@router.delete("/portfolio_history/{history_id}", status_code=204)
def delete_portfolio_history(
    history_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = (
        db.query(models.BacktestHistory)
        .filter(
            models.BacktestHistory.id == history_id,
            models.BacktestHistory.user_id == current_user.id,
            models.BacktestHistory.strategy_name.like(f"{_PORTFOLIO_STRATEGY_PREFIX}%"),
        )
        .first()
    )
    if not r:
        raise HTTPException(status_code=404, detail="History not found")
    db.delete(r)
    db.commit()
    return
