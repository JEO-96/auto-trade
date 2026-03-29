'use client';

import { useState, useEffect, useMemo } from 'react';
import { getExchangeMarkets } from '@/lib/api/keys';

const FALLBACK_SYMBOLS = ['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'];

// 주요 코인 — 항상 상단에 고정
const PINNED_SYMBOLS = [
    'BTC/KRW', 'ETH/KRW', 'XRP/KRW', 'SOL/KRW', 'DOGE/KRW', 'ADA/KRW',
    'AVAX/KRW', 'DOT/KRW', 'LINK/KRW', 'MATIC/KRW', 'ATOM/KRW', 'ETC/KRW',
];

// 모듈 레벨 캐시 — 같은 세션 내 중복 호출 방지
let cachedSymbols: string[] | null = null;

export function useMarkets(exchangeName: string = 'upbit') {
    const [rawSymbols, setRawSymbols] = useState<string[]>(cachedSymbols || FALLBACK_SYMBOLS);
    const [loading, setLoading] = useState(!cachedSymbols);

    useEffect(() => {
        if (cachedSymbols) return;

        let cancelled = false;
        getExchangeMarkets(exchangeName)
            .then((data) => {
                if (!cancelled && data.length > 0) {
                    cachedSymbols = data;
                    setRawSymbols(data);
                }
            })
            .catch(() => {
                // API 실패 시 폴백 유지
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [exchangeName]);

    // 주요 코인 상단 고정 + 나머지 알파벳 정렬
    const symbols = useMemo(() => {
        const pinned = PINNED_SYMBOLS.filter(s => rawSymbols.includes(s));
        const rest = rawSymbols.filter(s => !PINNED_SYMBOLS.includes(s));
        return [...pinned, ...rest];
    }, [rawSymbols]);

    return { symbols, loading, pinnedCount: PINNED_SYMBOLS.filter(s => rawSymbols.includes(s)).length };
}
