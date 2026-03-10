export const SYMBOLS = ['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'] as const;

export const STRATEGIES = [
    { value: 'james_pro_stable', label: '모멘텀 돌파 Pro (안정형)' },
    { value: 'james_pro_aggressive', label: '모멘텀 돌파 Pro (공격형)' },
    { value: 'james_pro_elite', label: '모멘텀 돌파 Elite' },
    { value: 'steady_compounder', label: '스테디 복리 (주간 안정형)' },
] as const;

export const BOT_STRATEGIES = [
    { value: 'momentum_breakout_basic', label: '모멘텀 돌파 (기본)' },
    { value: 'momentum_breakout_pro_stable', label: '모멘텀 돌파 Pro (안정형)' },
    { value: 'momentum_breakout_pro_aggressive', label: '모멘텀 돌파 Pro (공격형)' },
    { value: 'momentum_breakout_elite', label: '모멘텀 돌파 Elite' },
    { value: 'steady_compounder', label: '스테디 복리 (주간 안정형)' },
] as const;

export const BOT_TIMEFRAMES = [
    { value: '1m', label: '1분' },
    { value: '5m', label: '5분' },
    { value: '15m', label: '15분' },
    { value: '1h', label: '1시간' },
    { value: '4h', label: '4시간' },
    { value: '1d', label: '1일' },
] as const;

export const TIMEFRAMES = ['15m', '30m', '1h', '4h', '1d'] as const;

export const BOT_POLL_INTERVAL_MS = 10000;

export const BACKTEST_POLL_INTERVAL_MS = 1000;
