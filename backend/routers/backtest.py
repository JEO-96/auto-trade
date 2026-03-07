from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas
from dependencies import get_db, get_current_user
from core.backtester import Backtester
from core.portfolio_backtester import PortfolioBacktester

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.post("/", response_model=schemas.BacktestResponse)
def run_backtest(req: schemas.BacktestRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tester = Backtester(strategy_name=req.strategy_name)
        result = tester.run(
            symbol=req.symbol,
            timeframe=req.timeframe,
            limit=req.limit,
            initial_capital=req.initial_capital,
            start_date=req.start_date,
            end_date=req.end_date,
            db=db
        )
        return result
    except Exception as e:
        print(f"Backtest error: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/portfolio", response_model=schemas.BacktestResponse)
def run_portfolio_backtest(req: schemas.PortfolioBacktestRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tester = PortfolioBacktester(strategy_name=req.strategy_name)
        result = tester.run(
            symbols=req.symbols,
            timeframe=req.timeframe,
            limit=req.limit,
            initial_capital=req.initial_capital,
            start_date=req.start_date,
            end_date=req.end_date,
            db=db
        )
        return result
    except Exception as e:
        print(f"Portfolio Backtest error: {e}")
        return {"status": "error", "message": str(e)}
