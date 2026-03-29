'use client';

import { Settings2, Zap, Wallet } from 'lucide-react';
import { formatKRW, formatCryptoAmount } from '@/lib/utils';
import type { BalanceItem } from '@/lib/api/keys';

export interface SummaryStatsProps {
    botCount: number;
    activeBotCount: number;
    balances: BalanceItem[];
    onAssetDetailClick?: () => void;
    isAdmin?: boolean;
}

export default function SummaryStats({
    botCount,
    activeBotCount,
    balances,
    onAssetDetailClick,
    isAdmin = false,
}: SummaryStatsProps) {
    return (
        <div className={`grid grid-cols-1 ${isAdmin ? 'md:grid-cols-3' : 'md:grid-cols-2'} gap-4 mb-8`}>
            <div
                className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden opacity-0 animate-fade-in-up"
                style={{ animationDelay: '0ms' }}
            >
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-th-text-muted text-[11px] sm:text-xs font-semibold uppercase tracking-wider">전체 봇</h3>
                        <Settings2 className="w-4 h-4 text-primary" />
                    </div>
                    <span className="text-xl font-bold text-th-text">{botCount}개</span>
                </div>
            </div>

            <div
                className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden opacity-0 animate-fade-in-up"
                style={{ animationDelay: '80ms' }}
            >
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-th-text-muted text-[11px] sm:text-xs font-semibold uppercase tracking-wider">가동 중</h3>
                        <Zap className="w-4 h-4 text-secondary" />
                    </div>
                    <div className="flex items-center gap-2.5">
                        {activeBotCount > 0 && (
                            <div className="w-2.5 h-2.5 rounded-full bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-live-dot"></div>
                        )}
                        <span className="text-xl font-bold text-th-text">{activeBotCount}개</span>
                    </div>
                </div>
            </div>

            {isAdmin && (
                <button
                    type="button"
                    onClick={balances.length > 0 ? onAssetDetailClick : undefined}
                    className={`glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden text-left w-full opacity-0 animate-fade-in-up ${
                        balances.length > 0 ? 'cursor-pointer' : ''
                    }`}
                    style={{ animationDelay: '160ms' }}
                    aria-label="자산 상세보기 열기"
                    disabled={balances.length === 0}
                >
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-th-text-muted text-[11px] sm:text-xs font-semibold uppercase tracking-wider">UPBIT 자산</h3>
                            <Wallet className="w-4 h-4 text-primary" />
                        </div>
                        {balances.length > 0 ? (
                            <div className="space-y-1.5">
                                {balances.slice(0, 4).map((b) => (
                                    <div key={b.currency} className="flex justify-between items-center gap-2 min-w-0">
                                        <span className="text-xs font-medium text-th-text-secondary shrink-0">{b.currency}</span>
                                        <span className="text-xs font-bold text-th-text truncate">
                                            {b.currency === 'KRW'
                                                ? formatKRW(b.total)
                                                : formatCryptoAmount(b.total)}
                                        </span>
                                    </div>
                                ))}
                                <p className="text-[10px] sm:text-xs text-primary/70 text-right mt-2 hover:text-primary transition-colors">
                                    상세보기 &rarr;
                                </p>
                            </div>
                        ) : (
                            <span className="text-sm text-th-text-muted">API 키를 등록해주세요</span>
                        )}
                    </div>
                </button>
            )}
        </div>
    );
}
