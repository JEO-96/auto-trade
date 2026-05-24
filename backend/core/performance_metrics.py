import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_advanced_metrics(equity_series: pd.Series, trades: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calculate advanced performance metrics from an equity curve and trade history.
    """
    if equity_series.empty:
        return {}

    # Returns
    returns = equity_series.pct_change().dropna()
    
    # MDD (Max Drawdown)
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min())

    # Volatility (Annualized) - assuming 1h freq if not specified, 
    # but we'll just provide raw volatility if freq is unknown
    volatility = float(returns.std())

    # Sharpe Ratio (Assuming Risk Free Rate = 0 for simplicity in backtest)
    sharpe_ratio = 0.0
    if volatility > 0:
        sharpe_ratio = float(returns.mean() / returns.std() * np.sqrt(len(returns)))

    # Profit Factor
    profit_factor = 0.0
    if trades:
        pnls = [t.get('pnl', 0.0) for t in trades if t.get('side') == 'SELL']
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        if gross_loss > 0:
            profit_factor = float(gross_profit / gross_loss)
        elif gross_profit > 0:
            profit_factor = 999.0 # Infinite

    # Win Rate
    win_rate = 0.0
    if trades:
        pnls = [t.get('pnl', 0.0) for t in trades if t.get('side') == 'SELL']
        wins = [p for p in pnls if p > 0]
        if len(pnls) > 0:
            win_rate = float(len(wins) / len(pnls))

    return {
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "volatility": volatility,
        "profit_factor": profit_factor,
        "win_rate": win_rate
    }

def downsample_equity_curve(equity_curve: List[Dict[str, Any]], max_points: int = 500) -> List[Dict[str, Any]]:
    """
    Downsample equity curve to a maximum number of points for frontend performance.
    """
    if len(equity_curve) <= max_points:
        return equity_curve
    
    indices = np.linspace(0, len(equity_curve) - 1, max_points).astype(int)
    return [equity_curve[i] for i in indices]
