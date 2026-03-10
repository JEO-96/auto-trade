export interface BotConfig {
    id: number;
    user_id: number;
    symbol: string;
    timeframe: string;
    strategy_name?: string;
    is_active: boolean;
    paper_trading_mode: boolean;
    allocated_capital?: number;
    rsi_period?: number;
    macd_fast?: number;
    macd_slow?: number;
    volume_ma_period?: number;
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
