export const SYMBOLS = ['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'] as const;

export const STRATEGIES = [
    { value: 'james_pro_stable', label: '모멘텀 돌파 Pro (안정형)' },
    { value: 'james_pro_aggressive', label: '모멘텀 돌파 Pro (공격형)' },
    { value: 'james_pro_elite', label: '모멘텀 돌파 Elite' },
] as const;

export const TIMEFRAMES = ['15m', '30m', '1h', '4h', '1d'] as const;

export const BOT_POLL_INTERVAL_MS = 10000;

export const BACKTEST_POLL_INTERVAL_MS = 1000;
