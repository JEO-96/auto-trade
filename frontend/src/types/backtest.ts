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

export interface PriceChangePoint {
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
    price_changes?: Record<string, PriceChangePoint[]>;
    btc_benchmark?: PriceChangePoint[] | null;
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
    custom_sl_pct?: number;
    custom_tp_pct?: number;
    custom_trailing?: boolean;
    custom_rsi_period?: number;
    custom_rsi_threshold?: number;
    custom_adx_threshold?: number;
    custom_volume_multiplier?: number;
    custom_macd_fast?: number;
    custom_macd_slow?: number;
    custom_macd_signal?: number;
    custom_rsi_upper_limit?: number;
    custom_atr_period?: number;
    use_rsi_filter?: boolean;
    use_adx_filter?: boolean;
    use_volume_filter?: boolean;
    use_macd_filter?: boolean;
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
    custom_params: Record<string, unknown> | null;
    created_at: string;
}

export interface UserStrategy {
    id: number;
    name: string;
    base_strategy_name: string;
    custom_params: Record<string, unknown>;
    backtest_history_id: number | null;
    created_at: string;
}

export interface BacktestHistoryDetail extends BacktestHistoryItem {
    result_data: BacktestResult | null;
}

export interface RunBacktestResponse {
    status: 'running' | 'success';
    task_id?: string;
    message?: string;
    [key: string]: unknown;
}

// ──────────────────────────────────────────────
// 포트폴리오 백테스트 (Dual Momentum 등)
// ──────────────────────────────────────────────
export interface DualMomentumRequest {
    strategy_name?: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission_rate?: number;
    lookback_months?: number | null;
    evaluation_mode?: 'sequential' | 'best_momentum' | null;
    rebalance_freq?: 'monthly' | 'quarterly' | 'semiannual';
}

export interface PortfolioStrategyInfo {
    name: string;
    label: string;
    description: string;
    assets?: string[];
    min_data_year?: number;
}

export interface PortfolioTrade {
    date: string;
    side: 'BUY' | 'SELL';
    asset: string;
    price: number;
    units: number;
    cost?: number;
    proceeds?: number;
    fee: number;
}

export interface RebalanceLogEntry {
    date: string;
    selected_asset: string | null;
    weights: Record<string, number>;
    portfolio_value: number;
}

export interface PortfolioBacktestResult {
    strategy_name: string;
    assets: string[];
    initial_capital: number;
    final_capital: number;
    total_return: number;
    cagr: number;
    max_drawdown: number;
    sharpe: number;
    total_rebalances: number;
    holding_periods: Record<string, number>;
    equity_curve: EquityCurvePoint[];
    trades: PortfolioTrade[];
    rebalance_log: RebalanceLogEntry[];
    history_id?: number;
}

export interface PortfolioHistoryItem {
    id: number;
    title: string | null;
    strategy_name: string;
    assets: string[];
    initial_capital: number;
    final_capital: number | null;
    total_trades: number | null;
    start_date: string | null;
    end_date: string | null;
    commission_rate: number | null;
    status: string;
    created_at: string;
}

export interface PortfolioHistoryDetail extends PortfolioHistoryItem {
    result_data: PortfolioBacktestResult | null;
}
