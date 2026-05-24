import sys
import os
import asyncio
import pandas as pd
import numpy as np
import time
import psutil
import gc
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.optimization_engine import OptimizationEngine
from core.strategies.quick_swing_1h import QuickSwing1hStrategy

# Mock DataFetcher to avoid real network calls during test
from unittest.mock import MagicMock, AsyncMock
import core.data_fetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestOptimization")

async def run_test():
    # 1. Create Mock Data
    dates = pd.date_range(start="2024-01-01", periods=500, freq="1H")
    np.random.seed(42)
    close = 10000 + np.cumsum(np.random.normal(0, 50, size=500))
    df = pd.DataFrame({
        'open': close * (1 + np.random.normal(0, 0.001, 500)),
        'high': close * (1 + np.random.uniform(0, 0.005, 500)),
        'low': close * (1 - np.random.uniform(0, 0.005, 500)),
        'close': close,
        'volume': np.random.uniform(100, 1000, 500)
    }, index=dates)

    # Patch DataFetcher.fetch_ohlcv
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_ohlcv.return_value = df
    core.data_fetcher.DataFetcher = MagicMock(return_value=mock_fetcher)

    # 2. Define Parameter Grid (Reduced for quick check if no vbt)
    param_grid = {
        "backtest_sl_pct": [0.01, 0.02],
        "backtest_tp_pct": [0.03, 0.05]
    }
    
    total_combinations = len(param_grid["backtest_sl_pct"]) * len(param_grid["backtest_tp_pct"])
    logger.info(f"Testing with {total_combinations} combinations")

    # 3. Monitor memory
    process = psutil.Process(os.getpid())
    start_mem = process.memory_info().rss / (1024 * 1024)
    logger.info(f"Initial Memory: {start_mem:.2f} MB")

    # 4. Run Optimization
    engine = OptimizationEngine(chunk_size=100) # Small chunk size to verify logic
    
    start_time = time.time()
    results = await engine.run_grid_search(
        strategy_class=QuickSwing1hStrategy,
        symbol="BTC/USDT",
        interval="1H",
        start_date="2024-01-01",
        end_date="2024-03-01",
        param_grid=param_grid,
        metric="sharpe_ratio",
        top_n=10
    )
    duration = time.time() - start_time
    
    end_mem = process.memory_info().rss / (1024 * 1024)
    logger.info(f"Final Memory: {end_mem:.2f} MB")
    logger.info(f"Memory Delta: {end_mem - start_mem:.2f} MB")
    logger.info(f"Time taken: {duration:.2f} seconds")

    # 5. Verification
    if not results:
        logger.error("No results returned!")
        return

    logger.info(f"Top result: {results[0]}")
    
    assert len(results) <= 10
    assert "total_return" in results[0]
    assert "sharpe_ratio" in results[0]
    
    # Check if memory grew reasonably (considering we didn't force GC outside engine)
    # The engine does call gc.collect() per chunk
    if end_mem - start_mem > 200:
         logger.warning("Large memory growth detected!")
    else:
         logger.info("Memory usage seems stable.")

if __name__ == "__main__":
    asyncio.run(run_test())
