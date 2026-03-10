from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from dependencies import get_db, get_current_user
from core.vector_backtester import VectorBacktester, backtest_tasks

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.post("/", response_model=schemas.BacktestResponse)
def run_backtest(req: schemas.BacktestRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tester = VectorBacktester(strategy_name=req.strategy_name)
        # Start asynchronous task -- do NOT pass the request-scoped db session
        # to the background thread. The thread creates its own session internally.
        task_id = tester.start_async_backtest(
            symbols=[req.symbol],
            is_portfolio=False,
            timeframe=req.timeframe,
            limit=req.limit,
            initial_capital=req.initial_capital,
            start_date=req.start_date,
            end_date=req.end_date,
        )
        backtest_tasks[task_id]["user_id"] = current_user.id
        return {"status": "running", "task_id": task_id}
    except Exception as e:
        print(f"Backtest startup error: {e}")
        raise HTTPException(status_code=500, detail="Backtest failed to start")

@router.post("/portfolio", response_model=schemas.BacktestResponse)
def run_portfolio_backtest(req: schemas.PortfolioBacktestRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tester = VectorBacktester(strategy_name=req.strategy_name)
        # Start asynchronous portfolio task -- do NOT pass the request-scoped db session
        task_id = tester.start_async_backtest(
            symbols=req.symbols,
            is_portfolio=True,
            timeframe=req.timeframe,
            limit=req.limit,
            initial_capital=req.initial_capital,
            start_date=req.start_date,
            end_date=req.end_date,
        )
        backtest_tasks[task_id]["user_id"] = current_user.id
        return {"status": "running", "task_id": task_id}
    except Exception as e:
        print(f"Portfolio Backtest startup error: {e}")
        raise HTTPException(status_code=500, detail="Backtest failed to start")

@router.get("/status/{task_id}", response_model=schemas.BacktestTaskResponse)
def get_backtest_status(task_id: str, current_user: models.User = Depends(get_current_user)):
    if task_id not in backtest_tasks:
        raise HTTPException(status_code=404, detail="Backtest task not found")

    task_info = backtest_tasks[task_id]

    # Authorization: ensure the user can only access their own backtest results
    if task_info.get("user_id") and task_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this backtest")

    return {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info["progress"],
        "message": task_info["message"],
        "result": task_info["result"]
    }
