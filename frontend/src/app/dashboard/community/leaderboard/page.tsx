'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Trophy, Medal, TrendingUp, Users, BarChart2, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { getLeaderboard, getStrategyRankings } from '@/lib/api/community';
import { getStrategyLabel } from '@/lib/constants';
import type { LeaderboardEntry, StrategyRankingEntry } from '@/types/community';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

type Period = 'all' | 'monthly' | 'weekly';

const PERIOD_TABS: { value: Period; label: string }[] = [
    { value: 'all', label: '전체' },
    { value: 'monthly', label: '월간' },
    { value: 'weekly', label: '주간' },
];

function formatPnl(pnl: number): string {
    const formatted = Math.abs(pnl).toLocaleString('ko-KR', { maximumFractionDigits: 0 });
    return pnl >= 0 ? `+${formatted}` : `-${formatted}`;
}

function RankBadge({ rank }: { rank: number }) {
    if (rank === 1) {
        return (
            <div className="w-8 h-8 rounded-full bg-yellow-500/15 border border-yellow-500/30 flex items-center justify-center">
                <Trophy className="w-4 h-4 text-yellow-400" />
            </div>
        );
    }
    if (rank === 2) {
        return (
            <div className="w-8 h-8 rounded-full bg-gray-400/15 border border-gray-400/30 flex items-center justify-center">
                <Medal className="w-4 h-4 text-gray-300" />
            </div>
        );
    }
    if (rank === 3) {
        return (
            <div className="w-8 h-8 rounded-full bg-orange-500/15 border border-orange-500/30 flex items-center justify-center">
                <Medal className="w-4 h-4 text-orange-400" />
            </div>
        );
    }
    return (
        <div className="w-8 h-8 rounded-full bg-white/[0.04] flex items-center justify-center">
            <span className="text-xs font-bold text-gray-500">{rank}</span>
        </div>
    );
}

export default function LeaderboardPage() {
    const [period, setPeriod] = useState<Period>('all');
    const [rankings, setRankings] = useState<LeaderboardEntry[]>([]);
    const [strategies, setStrategies] = useState<StrategyRankingEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [strategyLoading, setStrategyLoading] = useState(true);

    const fetchLeaderboard = useCallback(async () => {
        setLoading(true);
        try {
            const data = await getLeaderboard(period, 20);
            setRankings(data.rankings);
        } catch {
            setRankings([]);
        } finally {
            setLoading(false);
        }
    }, [period]);

    const fetchStrategyRankings = useCallback(async () => {
        setStrategyLoading(true);
        try {
            const data = await getStrategyRankings();
            setStrategies(data.strategies);
        } catch {
            setStrategies([]);
        } finally {
            setStrategyLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchLeaderboard();
    }, [fetchLeaderboard]);

    useEffect(() => {
        fetchStrategyRankings();
    }, [fetchStrategyRankings]);

    return (
        <div className="p-6 pr-16 lg:p-8 lg:pr-8 max-w-6xl mx-auto space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
                    <Trophy className="w-6 h-6 text-yellow-400" />
                    리더보드
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                    트레이더 수익률 순위와 전략별 성과를 확인하세요
                </p>
            </div>

            {/* Period Tabs */}
            <div className="flex gap-1 bg-white/[0.03] rounded-xl p-1 w-fit border border-white/[0.04]">
                {PERIOD_TABS.map((tab) => (
                    <button
                        key={tab.value}
                        onClick={() => setPeriod(tab.value)}
                        className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                            period === tab.value
                                ? 'bg-primary/10 text-primary border border-primary/20'
                                : 'text-gray-500 hover:text-white hover:bg-white/[0.04]'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Leaderboard Table */}
            <div className="bg-surface/60 backdrop-blur-xl rounded-2xl border border-white/[0.04] overflow-hidden">
                <div className="px-6 py-4 border-b border-white/[0.04]">
                    <h2 className="text-base font-bold text-white">수익률 랭킹</h2>
                </div>

                {loading ? (
                    <div className="flex justify-center py-16">
                        <LoadingSpinner />
                    </div>
                ) : rankings.length === 0 ? (
                    <div className="text-center py-16 text-gray-500">
                        <BarChart2 className="w-10 h-10 mx-auto mb-3 text-gray-600" />
                        <p className="text-sm">아직 랭킹 데이터가 없습니다</p>
                        <p className="text-xs text-gray-600 mt-1">최소 5건 이상의 거래가 필요합니다</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-xs text-gray-500 uppercase tracking-wider">
                                    <th className="px-6 py-3 text-left font-semibold">순위</th>
                                    <th className="px-4 py-3 text-left font-semibold">트레이더</th>
                                    <th className="px-4 py-3 text-left font-semibold">전략</th>
                                    <th className="px-4 py-3 text-right font-semibold">총 PnL</th>
                                    <th className="px-4 py-3 text-right font-semibold">수익률</th>
                                    <th className="px-4 py-3 text-right font-semibold">승률</th>
                                    <th className="px-4 py-3 text-right font-semibold">거래</th>
                                    <th className="px-4 py-3 text-center font-semibold">유형</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/[0.03]">
                                {rankings.map((entry) => (
                                    <tr
                                        key={`${entry.rank}-${entry.nickname}`}
                                        className="hover:bg-white/[0.02] transition-colors"
                                    >
                                        <td className="px-6 py-3.5">
                                            <RankBadge rank={entry.rank} />
                                        </td>
                                        <td className="px-4 py-3.5">
                                            <span className="text-sm font-semibold text-white">
                                                {entry.nickname}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3.5">
                                            <span className="text-xs font-medium text-gray-400 bg-white/[0.04] px-2.5 py-1 rounded-md">
                                                {getStrategyLabel(entry.strategy_name)}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3.5 text-right">
                                            <div className="flex items-center justify-end gap-1">
                                                {entry.total_pnl >= 0 ? (
                                                    <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
                                                ) : (
                                                    <ArrowDownRight className="w-3.5 h-3.5 text-red-400" />
                                                )}
                                                <span className={`text-sm font-bold tabular-nums ${
                                                    entry.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                                                }`}>
                                                    {formatPnl(entry.total_pnl)}
                                                </span>
                                                <span className="text-[10px] text-gray-600 ml-0.5">KRW</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3.5 text-right">
                                            <span className={`text-sm font-bold tabular-nums ${
                                                entry.return_rate >= 0 ? 'text-emerald-400' : 'text-red-400'
                                            }`}>
                                                {entry.return_rate >= 0 ? '+' : ''}{entry.return_rate}%
                                            </span>
                                        </td>
                                        <td className="px-4 py-3.5 text-right">
                                            <span className="text-sm font-medium text-gray-300 tabular-nums">
                                                {entry.win_rate}%
                                            </span>
                                        </td>
                                        <td className="px-4 py-3.5 text-right">
                                            <span className="text-sm text-gray-400 tabular-nums">
                                                {entry.total_trades}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3.5 text-center">
                                            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${
                                                entry.is_live
                                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                                    : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                            }`}>
                                                {entry.is_live ? '실매매' : '모의투자'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Strategy Rankings */}
            <div>
                <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-primary" />
                    전략별 성과
                </h2>

                {strategyLoading ? (
                    <div className="flex justify-center py-12">
                        <LoadingSpinner />
                    </div>
                ) : strategies.length === 0 ? (
                    <div className="text-center py-12 text-gray-500 bg-surface/60 backdrop-blur-xl rounded-2xl border border-white/[0.04]">
                        <TrendingUp className="w-10 h-10 mx-auto mb-3 text-gray-600" />
                        <p className="text-sm">아직 전략 성과 데이터가 없습니다</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {strategies.map((strategy) => (
                            <div
                                key={strategy.strategy_name}
                                className="bg-surface/60 backdrop-blur-xl rounded-2xl border border-white/[0.04] p-5 hover:border-white/[0.08] transition-colors"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-sm font-bold text-white">
                                        {strategy.strategy_label}
                                    </h3>
                                    <div className="flex items-center gap-1.5 text-gray-500">
                                        <Users className="w-3.5 h-3.5" />
                                        <span className="text-xs font-medium">{strategy.total_users}명</span>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">평균 수익률</p>
                                        <p className={`text-lg font-bold tabular-nums ${
                                            strategy.avg_return_rate >= 0 ? 'text-emerald-400' : 'text-red-400'
                                        }`}>
                                            {strategy.avg_return_rate >= 0 ? '+' : ''}{strategy.avg_return_rate}%
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">평균 승률</p>
                                        <p className="text-lg font-bold text-white tabular-nums">
                                            {strategy.avg_win_rate}%
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">최고 수익률</p>
                                        <p className={`text-sm font-bold tabular-nums ${
                                            strategy.best_return_rate >= 0 ? 'text-emerald-400' : 'text-red-400'
                                        }`}>
                                            {strategy.best_return_rate >= 0 ? '+' : ''}{strategy.best_return_rate}%
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">총 거래</p>
                                        <p className="text-sm font-bold text-gray-300 tabular-nums">
                                            {strategy.total_trades.toLocaleString()}건
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
