import { useState, useEffect } from 'react';
import { getStrategies, type StrategyItem } from '@/lib/api/settings';
import { BOT_STRATEGIES, STRATEGIES } from '@/lib/constants';

interface UseStrategiesResult {
    botStrategies: StrategyItem[];
    backtestStrategies: StrategyItem[];
    loading: boolean;
}

/**
 * API에서 사용자 권한에 맞는 전략 목록을 가져옵니다.
 * 관리자: 전체 전략 표시 (비공개 포함)
 * 일반 사용자: 공개 전략만 표시
 * API 실패 시 하드코딩된 constants를 폴백으로 사용합니다.
 */
export function useStrategies(): UseStrategiesResult {
    const [botStrategies, setBotStrategies] = useState<StrategyItem[]>(
        BOT_STRATEGIES.map(s => ({ value: s.value, label: s.label, status: s.status }))
    );
    const [backtestStrategies, setBacktestStrategies] = useState<StrategyItem[]>(
        STRATEGIES.map(s => ({ value: s.value, label: s.label, status: s.status }))
    );
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;

        async function load() {
            try {
                const data = await getStrategies();
                if (cancelled) return;

                // 봇 전략 = strategies 목록 그대로
                setBotStrategies(data.strategies);

                // 백테스트 전략 = 별칭 + strategies 중 별칭에 없는 것
                const aliasValues = new Set(data.backtest_aliases.map(a => a.value));
                const backtestBase = data.backtest_aliases;
                for (const s of data.strategies) {
                    if (!aliasValues.has(s.value)) {
                        backtestBase.push(s);
                    }
                }
                setBacktestStrategies(backtestBase);
            } catch {
                // API 실패 시 fallback (constants) 유지
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, []);

    return { botStrategies, backtestStrategies, loading };
}
