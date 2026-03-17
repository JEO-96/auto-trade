'use client';

import { Settings2, Zap, Wallet } from 'lucide-react';
import { formatKRW, formatCryptoAmount } from '@/lib/utils';
import type { BalanceItem } from '@/lib/api/keys';

export interface SummaryStatsProps {
    botCount: number;
    activeBotCount: number;
    balances: BalanceItem[];
    onAssetDetailClick?: () => void;
}

export default function SummaryStats({
    botCount,
    activeBotCount,
    balances,
    onAssetDetailClick,
}: SummaryStatsProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden">
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">전체 봇</h3>
                        <Settings2 className="w-4 h-4 text-primary" />
                    </div>
                    <span className="text-xl font-bold text-white">{botCount}개</span>
                </div>
            </div>

            <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden">
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">가동 중</h3>
                        <Zap className="w-4 h-4 text-secondary" />
                    </div>
                    <div className="flex items-center gap-2.5">
                        {activeBotCount > 0 && (
                            <div className="w-2.5 h-2.5 rounded-full bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                        )}
                        <span className="text-xl font-bold text-white">{activeBotCount}개</span>
                    </div>
                </div>
            </div>

            <button
                type="button"
                onClick={balances.length > 0 ? onAssetDetailClick : undefined}
                className={`glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden text-left w-full ${
                    balances.length > 0 ? 'cursor-pointer' : ''
                }`}
                aria-label="자산 상세보기 열기"
                disabled={balances.length === 0}
            >
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">Upbit 자산</h3>
                        <Wallet className="w-4 h-4 text-primary" />
                    </div>
                    {balances.length > 0 ? (
                        <div className="space-y-1.5">
                            {balances.slice(0, 4).map((b) => (
                                <div key={b.currency} className="flex justify-between items-center gap-2 min-w-0">
                                    <span className="text-xs font-medium text-gray-400 shrink-0">{b.currency}</span>
                                    <span className="text-xs font-bold text-white truncate">
                                        {b.currency === 'KRW'
                                            ? formatKRW(b.total)
                                            : formatCryptoAmount(b.total)}
                                    </span>
                                </div>
                            ))}
                            <p className="text-[10px] text-primary/70 text-right mt-2 hover:text-primary transition-colors">
                                상세보기 &rarr;
                            </p>
                        </div>
                    ) : (
                        <span className="text-sm text-gray-500">API 키를 등록해주세요</span>
                    )}
                </div>
            </button>
        </div>
    );
}
