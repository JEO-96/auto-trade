'use client';

import { useState, useEffect } from 'react';
import { getExchangeMarkets } from '@/lib/api/keys';

const FALLBACK_SYMBOLS = ['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'];

// 모듈 레벨 캐시 — 같은 세션 내 중복 호출 방지
let cachedSymbols: string[] | null = null;

export function useMarkets(exchangeName: string = 'upbit') {
    const [symbols, setSymbols] = useState<string[]>(cachedSymbols || FALLBACK_SYMBOLS);
    const [loading, setLoading] = useState(!cachedSymbols);

    useEffect(() => {
        if (cachedSymbols) return;

        let cancelled = false;
        getExchangeMarkets(exchangeName)
            .then((data) => {
                if (!cancelled && data.length > 0) {
                    cachedSymbols = data;
                    setSymbols(data);
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

    return { symbols, loading };
}
