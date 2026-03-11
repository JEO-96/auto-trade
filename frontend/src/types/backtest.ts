export interface BacktestTrade {
    time: string;
    symbol?: string;
    side: 'BUY' | 'SELL';
    price: number;
    amount?: number;
    pnl: number;
    capital?: number;
}

export interface EquityCurvePoint {
    time: string;
    value: number;
}

export interface BacktestMetrics {
    win_rate?: number;
    profit_factor?: number;
    max_drawdown_pct?: number;
    sharpe_ratio?: number;
    sortino_ratio?: number;
    avg_win?: number;
    avg_loss?: number;
    win_count?: number;
    loss_count?: number;
    best_trade?: number;
    worst_trade?: number;
    max_consecutive_wins?: number;
    max_consecutive_losses?: number;
    total_return_pct?: number;
    cagr_pct?: number;
    calmar_ratio?: number;
    avg_holding_hours?: number;
    expectancy?: number;
}

export interface BacktestResult {
    status?: string;
    initial_capital: number;
    final_capital: number;
    total_trades: number;
    trades: BacktestTrade[];
    equity_curve?: EquityCurvePoint[];
    metrics?: BacktestMetrics;
}

export interface BacktestFormParams {
    symbols: string[];
    timeframe: string;
    strategy_name: string;
    limit: number | null;
    initial_capital: number;
    start_date: string | null;
    end_date: string | null;
    commission_rate?: number;
}

export interface BacktestTaskStatus {
    status: 'running' | 'completed' | 'failed';
    progress: number;
    message: string;
    result?: BacktestResult;
}

export interface BacktestHistoryItem {
    id: number;
    symbols: string[];
    timeframe: string;
    strategy_name: string;
    initial_capital: number;
    final_capital: number | null;
    total_trades: number | null;
    status: string;
    created_at: string;
}

export interface BacktestHistoryDetail extends BacktestHistoryItem {
    result_data: BacktestResult | null;
}
