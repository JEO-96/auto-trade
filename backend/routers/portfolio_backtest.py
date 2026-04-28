"""포트폴리오 백테스트 라우터 — ETF Dual Momentum 등 다자산 전략."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import models
from core.portfolio_backtester import PortfolioBacktester
from dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["portfolio-backtest"])


class DualMomentumRequest(BaseModel):
    strategy_name: str = Field(default="dual_momentum_etf_v1")
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    initial_capital: float = Field(default=10_000_000)
    commission_rate: float = Field(default=0.001)


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
        )
        result = tester.run(
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            db=db,
        )
        return result
    except ValueError as e:
        # 알 수 없는 전략명, 잘못된 날짜 등
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Dual momentum backtest failed: %s", e)
        raise HTTPException(status_code=500, detail="Portfolio backtest failed")
