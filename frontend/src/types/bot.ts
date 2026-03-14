export interface BotConfig {
    id: number;
    user_id?: number;
    symbol: string;
    timeframe: string;
    exchange_name: string;
    strategy_name: string;
    paper_trading_mode: boolean;
    allocated_capital: number;
    is_active: boolean;
    rsi_period: number;
    volume_ma_period: number;
    macd_fast?: number;
    macd_slow?: number;
}

export interface BotCreateRequest {
    symbol: string;
    timeframe?: string;
    exchange_name?: string;
    strategy_name?: string;
    paper_trading_mode?: boolean;
    allocated_capital?: number;
}

export interface BotMultiCreateRequest {
    symbols: string[];
    timeframe?: string;
    exchange_name?: string;
    strategy_name?: string;
    paper_trading_mode?: boolean;
    allocated_capital?: number;
}

export interface TradeLog {
    id: number;
    bot_id: number;
    symbol: string;
    side: 'BUY' | 'SELL';
    price: number;
    amount: number;
    pnl?: number;
    reason: string;
    timestamp: string;
}

export interface BotStatus {
    bot_status: 'Running' | 'Stopped';
}

export interface ActiveBotPublic {
    nickname: string | null;
    symbol: string;
    timeframe: string;
    strategy_name: string | null;
    paper_trading_mode: boolean;
}

export interface DailyPnl {
    date: string;
    pnl: number;
    cumulative_pnl: number;
}

export interface WeeklyPnl {
    week: string;
    pnl: number;
}

export interface BotPerformance {
    bot_id: number;
    total_pnl: number;
    total_trades: number;
    win_rate: number;
    max_drawdown: number;
    daily_pnl: DailyPnl[];
    weekly_pnl: WeeklyPnl[];
}
