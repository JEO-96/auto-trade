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

export interface BacktestResult {
    status?: string;
    initial_capital: number;
    final_capital: number;
    total_trades: number;
    trades: BacktestTrade[];
    equity_curve?: EquityCurvePoint[];
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
    title: string | null;
    symbols: string[];
    timeframe: string;
    strategy_name: string;
    initial_capital: number;
    final_capital: number | null;
    total_trades: number | null;
    status: string;
    start_date: string | null;
    end_date: string | null;
    commission_rate: number | null;
    created_at: string;
}

export interface BacktestHistoryDetail extends BacktestHistoryItem {
    result_data: BacktestResult | null;
}
