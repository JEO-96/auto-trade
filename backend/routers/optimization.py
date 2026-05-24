from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import importlib
import logging

from core.optimization_engine import OptimizationEngine
from auth import get_current_user

router = APIRouter(prefix="/optimization", tags=["optimization"])
logger = logging.getLogger(__name__)

class OptimizationRequest(BaseModel):
    strategy_name: str
    symbol: str
    interval: str
    start_date: str
    end_date: str
    param_grid: Dict[str, List[Any]]
    metric: str = "sharpe_ratio"
    top_n: int = 10

@router.post("/run")
async def run_optimization(req: OptimizationRequest, current_user: Any = Depends(get_current_user)):
    """
    Run grid search optimization for a specific strategy and parameter grid.
    """
    try:
        # Dynamically load the strategy class
        # Assuming strategy files are in backend/core/strategies/ and class names match
        # We need to map strategy_name (e.g., 'TrendRiderV4') to module and class
        # For simplicity, we assume strategy_name is the module name and 
        # we'll look for a class that inherits from BaseStrategy.
        
        module_path = f"backend.core.strategies.{req.strategy_name}"
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            raise HTTPException(status_code=400, detail=f"Strategy module {req.strategy_name} not found")

        # Find the strategy class in the module
        strategy_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and name != 'BaseStrategy' and hasattr(obj, 'check_buy_signal'):
                strategy_class = obj
                break
        
        if not strategy_class:
            raise HTTPException(status_code=400, detail=f"No suitable strategy class found in {req.strategy_name}")

        engine = OptimizationEngine(chunk_size=500) # Smaller chunk for RAM safety
        results = await engine.run_grid_search(
            strategy_class=strategy_class,
            symbol=req.symbol,
            interval=req.interval,
            start_date=req.start_date,
            end_date=req.end_date,
            param_grid=req.param_grid,
            metric=req.metric,
            top_n=req.top_n
        )

        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        logger.error(f"Optimization error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
