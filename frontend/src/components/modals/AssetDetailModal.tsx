'use client';

import { useMemo } from 'react';
import { X, PieChart, TrendingUp } from 'lucide-react';
import { formatKRW, formatCryptoAmount } from '@/lib/utils';
import type { BalanceItem } from '@/lib/api/keys';

export interface AssetDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    balances: BalanceItem[];
}

/* ── Palette for donut chart segments ── */
const CHART_COLORS = [
    '#6366f1', // indigo
    '#10b981', // emerald
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#06b6d4', // cyan
    '#ec4899', // pink
    '#14b8a6', // teal
    '#f97316', // orange
    '#64748b', // slate
];

interface AssetWithValue {
    currency: string;
    total: number;
    free: number;
    avgBuyPrice: number | null;
    estimatedKRW: number;
}

function computeAssets(balances: BalanceItem[]): AssetWithValue[] {
    return balances
        .map((b) => {
            let estimatedKRW: number;
            if (b.currency === 'KRW') {
                estimatedKRW = b.total;
            } else {
                estimatedKRW = b.avg_buy_price ? b.total * b.avg_buy_price : 0;
            }
            return {
                currency: b.currency,
                total: b.total,
                free: b.free,
                avgBuyPrice: b.avg_buy_price,
                estimatedKRW,
            };
        })
        .sort((a, b) => b.estimatedKRW - a.estimatedKRW);
}

/* ── SVG Donut Chart ── */
function DonutChart({ assets, totalValue }: { assets: AssetWithValue[]; totalValue: number }) {
    const radius = 80;
    const strokeWidth = 28;
    const center = 100;
    const circumference = 2 * Math.PI * radius;

    const segments = useMemo(() => {
        if (totalValue === 0) return [];
        let accumulated = 0;
        return assets
            .filter((a) => a.estimatedKRW > 0)
            .map((a, i) => {
                const ratio = a.estimatedKRW / totalValue;
                const dashLength = ratio * circumference;
                const dashOffset = circumference - accumulated * circumference;
                accumulated += ratio;
                return {
                    currency: a.currency,
                    ratio,
                    color: CHART_COLORS[i % CHART_COLORS.length],
                    dashLength,
                    dashOffset,
                };
            });
    }, [assets, totalValue, circumference]);

    return (
        <div className="flex flex-col items-center gap-4">
            <svg
                width="200"
                height="200"
                viewBox="0 0 200 200"
                className="transform -rotate-90"
                role="img"
                aria-label="자산 배분 도넛 차트"
            >
                {/* Background ring */}
                <circle
                    cx={center}
                    cy={center}
                    r={radius}
                    fill="none"
                    stroke="rgba(255,255,255,0.04)"
                    strokeWidth={strokeWidth}
                />
                {segments.map((seg) => (
                    <circle
                        key={seg.currency}
                        cx={center}
                        cy={center}
                        r={radius}
                        fill="none"
                        stroke={seg.color}
                        strokeWidth={strokeWidth}
                        strokeDasharray={`${seg.dashLength} ${circumference - seg.dashLength}`}
                        strokeDashoffset={seg.dashOffset}
                        strokeLinecap="butt"
                        className="transition-all duration-500"
                    />
                ))}
            </svg>

            {/* Legend */}
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5">
                {segments.map((seg) => (
                    <div key={seg.currency} className="flex items-center gap-1.5">
                        <div
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: seg.color }}
                        />
                        <span className="text-xs text-gray-400">
                            {seg.currency}{' '}
                            <span className="text-gray-600">
                                {(seg.ratio * 100).toFixed(1)}%
                            </span>
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default function AssetDetailModal({ isOpen, onClose, balances }: AssetDetailModalProps) {
    const assets = useMemo(() => computeAssets(balances), [balances]);
    const totalValue = useMemo(
        () => assets.reduce((sum, a) => sum + a.estimatedKRW, 0),
        [assets],
    );

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
            role="dialog"
            aria-modal="true"
            aria-label="자산 상세보기"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
            onKeyDown={(e) => {
                if (e.key === 'Escape') onClose();
            }}
        >
            <div className="w-full max-w-2xl max-h-[90vh] bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl flex flex-col overflow-hidden">
                {/* ── Header ── */}
                <div className="flex items-center justify-between p-6 border-b border-white/[0.06] shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">
                            <PieChart className="w-5 h-5 text-primary" />
                        </div>
                        <h2 className="text-base font-bold text-white">자산 상세보기</h2>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="닫기"
                        className="text-gray-500 hover:text-gray-300 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* ── Content (scrollable) ── */}
                <div className="overflow-y-auto flex-1 p-6 space-y-6">
                    {/* Total portfolio value */}
                    <div className="glass-panel rounded-xl p-5 text-center">
                        <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-1">
                            총 자산 평가액
                        </p>
                        <div className="flex items-center justify-center gap-2">
                            <TrendingUp className="w-5 h-5 text-secondary" />
                            <span className="text-2xl font-bold text-white">
                                {formatKRW(totalValue)}
                            </span>
                        </div>
                        <p className="text-xs text-gray-600 mt-1">
                            {assets.length}개 자산 보유
                        </p>
                    </div>

                    {/* Chart + Table layout */}
                    <div className="flex flex-col md:flex-row gap-6">
                        {/* Donut chart */}
                        <div className="md:w-[240px] shrink-0 flex justify-center">
                            <DonutChart assets={assets} totalValue={totalValue} />
                        </div>

                        {/* Table */}
                        <div className="flex-1 min-w-0">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left" role="table">
                                    <thead>
                                        <tr className="border-b border-white/[0.06]">
                                            <th className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 pb-2 pr-2">
                                                자산
                                            </th>
                                            <th className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 pb-2 pr-2 text-right">
                                                보유량
                                            </th>
                                            <th className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 pb-2 pr-2 text-right hidden sm:table-cell">
                                                가용
                                            </th>
                                            <th className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 pb-2 pr-2 text-right hidden sm:table-cell">
                                                평균 매수가
                                            </th>
                                            <th className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 pb-2 text-right">
                                                평가 금액
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {assets.map((a, i) => {
                                            const pct =
                                                totalValue > 0
                                                    ? ((a.estimatedKRW / totalValue) * 100).toFixed(1)
                                                    : '0.0';
                                            return (
                                                <tr
                                                    key={a.currency}
                                                    className="border-b border-white/[0.03] last:border-b-0 hover:bg-white/[0.02] transition-colors"
                                                >
                                                    <td className="py-2.5 pr-2">
                                                        <div className="flex items-center gap-2">
                                                            <div
                                                                className="w-2 h-2 rounded-full shrink-0"
                                                                style={{
                                                                    backgroundColor:
                                                                        CHART_COLORS[i % CHART_COLORS.length],
                                                                }}
                                                            />
                                                            <span className="text-xs font-bold text-white">
                                                                {a.currency}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="py-2.5 pr-2 text-right">
                                                        <span className="text-xs font-medium text-gray-300 font-mono">
                                                            {a.currency === 'KRW'
                                                                ? formatKRW(a.total)
                                                                : formatCryptoAmount(a.total)}
                                                        </span>
                                                    </td>
                                                    <td className="py-2.5 pr-2 text-right hidden sm:table-cell">
                                                        <span className="text-xs text-gray-500 font-mono">
                                                            {a.currency === 'KRW'
                                                                ? formatKRW(a.free)
                                                                : formatCryptoAmount(a.free)}
                                                        </span>
                                                    </td>
                                                    <td className="py-2.5 pr-2 text-right hidden sm:table-cell">
                                                        <span className="text-xs text-gray-500 font-mono">
                                                            {a.avgBuyPrice != null
                                                                ? formatKRW(a.avgBuyPrice)
                                                                : '-'}
                                                        </span>
                                                    </td>
                                                    <td className="py-2.5 text-right">
                                                        <div>
                                                            <span className="text-xs font-bold text-white font-mono">
                                                                {formatKRW(a.estimatedKRW)}
                                                            </span>
                                                            <span className="text-[10px] text-gray-600 ml-1.5">
                                                                {pct}%
                                                            </span>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>

                            {assets.length === 0 && (
                                <p className="text-sm text-gray-600 text-center py-8">
                                    보유 자산이 없습니다.
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
