"""포트폴리오 백테스트 라우터 — ETF Dual Momentum 등 다자산 전략."""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import models
from core.portfolio_backtester import PortfolioBacktester
from core.portfolio_strategy_registry import list_portfolio_strategies
from dependencies import get_current_user, get_db

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


@router.post("/dual_momentum/")
def run_dual_momentum_backtest(
    req: DualMomentumRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        )
        # 결과 저장 (실패해도 결과 반환은 막지 않음)
        try:
            history_id = _save_history(db, current_user.id, req, result)
            result["history_id"] = history_id
        except Exception as e:
            logger.warning("Failed to save portfolio backtest history: %s", e)
        return result
    except ValueError as e:
        # 알 수 없는 전략명, 잘못된 날짜 등
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Dual momentum backtest failed: %s", e)
        raise HTTPException(status_code=500, detail="Portfolio backtest failed")


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
