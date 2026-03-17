export const SYMBOLS = ['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'] as const;

export const EXCHANGES = [
    { value: 'upbit', label: '업비트 (Upbit)' },
    { value: 'bithumb', label: '빗썸 (Bithumb)' },
] as const;

export const BOT_STRATEGIES = [
    { value: 'trend_rider_4h', label: '트렌드 라이더 (4시간)', status: 'confirmed' as const },
    { value: 'momentum_basic_1h', label: '모멘텀 기본 (1시간)', status: 'testing' as const },
    { value: 'momentum_basic_4h', label: '모멘텀 기본 (4시간)', status: 'testing' as const },
    { value: 'momentum_basic_1d', label: '모멘텀 기본 (1일)', status: 'testing' as const },
    { value: 'momentum_stable_1h', label: '모멘텀 안정형 (1시간)', status: 'testing' as const },
    { value: 'momentum_stable_4h', label: '모멘텀 안정형 (4시간)', status: 'testing' as const },
    { value: 'momentum_stable_1d', label: '모멘텀 안정형 (1일)', status: 'testing' as const },
    { value: 'momentum_aggressive_1h', label: '모멘텀 공격형 (1시간)', status: 'testing' as const },
    { value: 'momentum_aggressive_4h', label: '모멘텀 공격형 (4시간)', status: 'testing' as const },
    { value: 'momentum_aggressive_1d', label: '모멘텀 공격형 (1일)', status: 'testing' as const },
    { value: 'multi_signal_1h', label: '멀티시그널 (1시간)', status: 'testing' as const },
    { value: 'multi_signal_4h', label: '멀티시그널 (4시간)', status: 'testing' as const },
    { value: 'multi_signal_1d', label: '멀티시그널 (1일)', status: 'testing' as const },
    { value: 'quick_swing_1h', label: '퀵 스윙 (1시간)', status: 'testing' as const },
    { value: 'wide_swing_1d', label: '와이드 스윙 (1일)', status: 'testing' as const },
    { value: 'scalper_15m', label: '스캘퍼 (15분)', status: 'testing' as const },
    { value: 'quick_swing_15m', label: '퀵 스윙 (15분)', status: 'testing' as const },
    { value: 'multi_signal_15m', label: '멀티시그널 (15분)', status: 'testing' as const },
    { value: 'trend_follower_15m', label: '추세추종 (15분)', status: 'testing' as const },
] as const;

/** 백테스트 전용 전략 */
export const STRATEGIES = [
    { value: 'trend_rider_4h', label: '트렌드 라이더 (4시간)', status: 'confirmed' as const },
    { value: 'momentum_basic_1h', label: '모멘텀 기본 (1시간)', status: 'testing' as const },
    { value: 'momentum_basic_4h', label: '모멘텀 기본 (4시간)', status: 'testing' as const },
    { value: 'momentum_basic_1d', label: '모멘텀 기본 (1일)', status: 'testing' as const },
    { value: 'momentum_stable_1h', label: '모멘텀 안정형 (1시간)', status: 'testing' as const },
    { value: 'momentum_stable_4h', label: '모멘텀 안정형 (4시간)', status: 'testing' as const },
    { value: 'momentum_stable_1d', label: '모멘텀 안정형 (1일)', status: 'testing' as const },
    { value: 'momentum_aggressive_1h', label: '모멘텀 공격형 (1시간)', status: 'testing' as const },
    { value: 'momentum_aggressive_4h', label: '모멘텀 공격형 (4시간)', status: 'testing' as const },
    { value: 'momentum_aggressive_1d', label: '모멘텀 공격형 (1일)', status: 'testing' as const },
    { value: 'multi_signal_1h', label: '멀티시그널 (1시간)', status: 'testing' as const },
    { value: 'multi_signal_4h', label: '멀티시그널 (4시간)', status: 'testing' as const },
    { value: 'multi_signal_1d', label: '멀티시그널 (1일)', status: 'testing' as const },
    { value: 'quick_swing_1h', label: '퀵 스윙 (1시간)', status: 'testing' as const },
    { value: 'wide_swing_1d', label: '와이드 스윙 (1일)', status: 'testing' as const },
    { value: 'scalper_15m', label: '스캘퍼 (15분)', status: 'testing' as const },
    { value: 'quick_swing_15m', label: '퀵 스윙 (15분)', status: 'testing' as const },
    { value: 'multi_signal_15m', label: '멀티시그널 (15분)', status: 'testing' as const },
    { value: 'trend_follower_15m', label: '추세추종 (15분)', status: 'testing' as const },
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

export const BOT_STATUS = { RUNNING: 'Running', STOPPED: 'Stopped' } as const;

export const TRADE_SIDE = { BUY: 'BUY', SELL: 'SELL' } as const;

export const TRADE_SIDE_LABELS: Record<string, string> = { BUY: '매수', SELL: '매도' };

export const BOT_MODE_LABELS = { paper: '모의투자', live: '실매매' } as const;

export const BOT_POLL_INTERVAL_MS = 10000;

export const BACKTEST_POLL_INTERVAL_MS = 1000;

/** 봇 전략 → 백테스트 전략 매핑 (동일 이름 체계) */
export const BOT_TO_BACKTEST_STRATEGY: Record<string, string> = Object.fromEntries(
    BOT_STRATEGIES.map(s => [s.value, s.value]),
);

/** 전략 value → 사용자 친화적 label 맵 (BOT_STRATEGIES + STRATEGIES 통합) */
const STRATEGY_LABEL_MAP: Record<string, string> = {
    ...Object.fromEntries([
        ...BOT_STRATEGIES.map(s => [s.value, s.label]),
        ...STRATEGIES.map(s => [s.value, s.label]),
    ]),
    // Legacy aliases (기존 DB 데이터 표시용)
    'momentum_breakout_basic': '모멘텀 돌파 (기본)',
    'momentum_breakout_pro_stable': '모멘텀 돌파 Pro (안정형)',
    'momentum_breakout_pro_aggressive': '모멘텀 돌파 Pro (공격형)',
    'momentum_breakout_elite': '멀티시그널',
    'momentum_elite_1h': '멀티시그널 (1시간)',
    'momentum_elite_4h': '멀티시그널 (4시간)',
    'momentum_elite_1d': '멀티시그널 (1일)',
    'steady_compounder_1h': '퀵 스윙 (1시간)',
    'steady_compounder_1d': '와이드 스윙 (1일)',
    'james_basic': '모멘텀 돌파 (기본)',
    'james_pro_stable': '모멘텀 돌파 Pro (안정형)',
    'james_pro_aggressive': '모멘텀 돌파 Pro (공격형)',
    'james_pro_elite': '멀티시그널',
    'steady_compounder': '트렌드 라이더 (주간 안정형)',
    'steady_compounder_v1': '트렌드 라이더 V1 (백업)',
};

/**
 * 전략 내부 이름에서 사용자 친화적 레이블을 반환합니다.
 * 매핑이 없으면 원래 이름을 그대로 반환합니다.
 */
export function getStrategyLabel(strategyName: string): string {
    return STRATEGY_LABEL_MAP[strategyName] ?? strategyName;
}

/** 전략 이름 → 고정 타임프레임 매핑 (자동 생성) */
const STRATEGY_TIMEFRAME_MAP: Record<string, string> = Object.fromEntries(
    BOT_STRATEGIES.map(s => {
        const match = s.value.match(/_(\d+[mhd])$/);
        return [s.value, match ? match[1] : '1d'];
    }),
);

/**
 * 전략 이름에서 고정 타임프레임을 추출합니다.
 * 매핑에 없으면 이름 끝의 타임프레임 패턴(_1h, _4h, _1d 등)을 파싱합니다.
 * 파싱도 실패하면 '1d'를 기본값으로 반환합니다.
 */
export function getStrategyTimeframe(strategyName: string): string {
    if (STRATEGY_TIMEFRAME_MAP[strategyName]) {
        return STRATEGY_TIMEFRAME_MAP[strategyName];
    }
    const match = strategyName.match(/_(\d+[mhd])$/);
    return match ? match[1] : '1d';
}

/**
 * 거래소 내부 이름에서 사용자 친화적 레이블을 반환합니다.
 * 매핑이 없으면 원래 이름을 그대로 반환합니다.
 */
export function getExchangeLabel(exchange: string): string {
    const found = EXCHANGES.find(e => e.value === exchange);
    return found?.label ?? exchange;
}

/** 타임프레임 value → label 매핑 (공통) */
export const TIMEFRAME_LABEL_MAP: Record<string, string> = Object.fromEntries(
    BOT_TIMEFRAMES.map(t => [t.value, t.label]),
);

/** 백테스트/설정에서 제외할 초단기 타임프레임 */
export const EXCLUDED_SHORT_TIMEFRAMES = ['1m', '5m'] as const;

/** 백테스트/설정용 타임프레임 (초단기 제외) */
export const BACKTEST_TIMEFRAMES = BOT_TIMEFRAMES.filter(
    t => !(EXCLUDED_SHORT_TIMEFRAMES as readonly string[]).includes(t.value),
);

/** 실시간 봇 현황 폴링 간격 (ms) */
export const LIVE_BOTS_POLL_INTERVAL_MS = 15000;

/** 차트 컬러 팔레트 (도넛차트, 자산 분포 등) */
export const CHART_COLORS = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#64748b',
] as const;
