'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
    ResponsiveContainer,
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Cell,
    ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, Activity, Target, BarChart2 } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer';
import StatCard from '@/components/ui/StatCard';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { getBotList, getBotPerformance } from '@/lib/api/bot';
import { getStrategyLabel } from '@/lib/constants';
import type { BotConfig } from '@/types/bot';
import type { BotPerformance } from '@/types/bot';

export default function PerformancePage() {
    const [bots, setBots] = useState<BotConfig[]>([]);
    const [selectedBotId, setSelectedBotId] = useState<number | null>(null);
    const [performance, setPerformance] = useState<BotPerformance | null>(null);
    const [loading, setLoading] = useState(true);
    const [perfLoading, setPerfLoading] = useState(false);

    // 봇 목록 로드
    useEffect(() => {
        getBotList()
            .then((list) => {
                setBots(list);
                if (list.length > 0) {
                    setSelectedBotId(list[0].id);
                }
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    // 선택된 봇의 성과 로드
    const loadPerformance = useCallback(async (botId: number) => {
        setPerfLoading(true);
        try {
            const data = await getBotPerformance(botId);
            setPerformance(data);
        } catch {
            setPerformance(null);
        } finally {
            setPerfLoading(false);
        }
    }, []);

    useEffect(() => {
        if (selectedBotId !== null) {
            loadPerformance(selectedBotId);
        }
    }, [selectedBotId, loadPerformance]);

    const formatAxisKRW = (value: number) => {
        if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
        if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
        return value.toLocaleString();
    };

    if (loading) {
        return (
            <PageContainer>
                <div className="flex items-center justify-center min-h-[60vh]">
                    <LoadingSpinner message="봇 목록 로딩 중..." />
                </div>
            </PageContainer>
        );
    }

    if (bots.length === 0) {
        return (
            <PageContainer>
                <div className="mb-8">
                    <h1 className="text-2xl font-bold tracking-tight">성과 분석</h1>
                    <p className="text-th-text-muted text-sm mt-1">봇의 매매 성과를 분석합니다</p>
                </div>
                <EmptyState
                    icon={<BarChart2 className="w-12 h-12" />}
                    title="생성된 봇이 없습니다"
                    description="대시보드에서 봇을 먼저 생성해주세요."
                />
            </PageContainer>
        );
    }

    const selectedBot = bots.find(b => b.id === selectedBotId);

    return (
        <PageContainer>
            {/* 헤더 */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">성과 분석</h1>
                    <p className="text-th-text-muted text-sm mt-1">봇의 매매 성과를 분석합니다</p>
                </div>
                <select
                    value={selectedBotId ?? ''}
                    onChange={(e) => setSelectedBotId(Number(e.target.value))}
                    className="bg-surface border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-th-text focus:outline-none focus:border-primary/50 transition-colors"
                >
                    {bots.map((bot) => (
                        <option key={bot.id} value={bot.id}>
                            {bot.symbol} · {getStrategyLabel(bot.strategy_name)} · {bot.paper_trading_mode ? '모의' : '실매매'}
                        </option>
                    ))}
                </select>
            </div>

            {perfLoading ? (
                <div className="flex items-center justify-center min-h-[40vh]">
                    <LoadingSpinner message="성과 데이터 로딩 중..." />
                </div>
            ) : !performance || performance.total_trades === 0 ? (
                <EmptyState
                    icon={<Activity className="w-12 h-12" />}
                    title="거래 내역이 없습니다"
                    description={selectedBot ? `${selectedBot.symbol} 봇의 거래가 아직 발생하지 않았습니다.` : undefined}
                />
            ) : (
                <>
                    {/* 통계 카드 */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <StatCard
                            title="총 손익"
                            value={
                                <span className={performance.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                                    {performance.total_pnl >= 0 ? '+' : ''}{performance.total_pnl.toLocaleString()}원
                                </span>
                            }
                            icon={performance.total_pnl >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                            accentColor={performance.total_pnl >= 0 ? 'from-emerald-500/10' : 'from-red-500/10'}
                        />
                        <StatCard
                            title="승률"
                            value={`${performance.win_rate}%`}
                            icon={<Target className="w-5 h-5" />}
                            subtitle={
                                <span className="text-th-text-muted">{performance.total_trades}건 거래</span>
                            }
                        />
                        <StatCard
                            title="총 거래 수"
                            value={`${performance.total_trades}건`}
                            icon={<Activity className="w-5 h-5" />}
                        />
                        <StatCard
                            title="최대 드로다운"
                            value={
                                <span className={performance.max_drawdown < 0 ? 'text-red-400' : 'text-th-text-secondary'}>
                                    {performance.max_drawdown}%
                                </span>
                            }
                            icon={<TrendingDown className="w-5 h-5" />}
                            accentColor="from-red-500/10"
                        />
                    </div>

                    {/* 누적 PnL 차트 */}
                    <div className="glass-panel rounded-2xl p-6 mb-6">
                        <h2 className="text-sm font-semibold text-th-text-secondary uppercase tracking-wider mb-4">누적 손익</h2>
                        <div className="h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={performance.daily_pnl}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickFormatter={(v: string) => v.slice(5)}
                                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                                    />
                                    <YAxis
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickFormatter={formatAxisKRW}
                                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#1a1a2e',
                                            border: '1px solid rgba(255,255,255,0.08)',
                                            borderRadius: '12px',
                                            color: '#fff',
                                            fontSize: '13px',
                                        }}
                                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                        formatter={(value: any) => [`${Number(value).toLocaleString()}원`, '누적 손익']}
                                        labelFormatter={(label) => String(label)}
                                    />
                                    <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                                    <Line
                                        type="monotone"
                                        dataKey="cumulative_pnl"
                                        stroke="#6366f1"
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{ r: 4, fill: '#6366f1' }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* 일별 PnL 막대 차트 */}
                    <div className="glass-panel rounded-2xl p-6 mb-6">
                        <h2 className="text-sm font-semibold text-th-text-secondary uppercase tracking-wider mb-4">일별 손익</h2>
                        <div className="h-[300px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={performance.daily_pnl}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickFormatter={(v: string) => v.slice(5)}
                                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                                    />
                                    <YAxis
                                        tick={{ fill: '#6b7280', fontSize: 11 }}
                                        tickFormatter={formatAxisKRW}
                                        axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#1a1a2e',
                                            border: '1px solid rgba(255,255,255,0.08)',
                                            borderRadius: '12px',
                                            color: '#fff',
                                            fontSize: '13px',
                                        }}
                                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                        formatter={(value: any) => [`${Number(value).toLocaleString()}원`, '일별 손익']}
                                        labelFormatter={(label) => String(label)}
                                    />
                                    <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                                    <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                                        {performance.daily_pnl.map((entry, index) => (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'}
                                                fillOpacity={0.8}
                                            />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* 주별 PnL 테이블 */}
                    {performance.weekly_pnl.length > 0 && (
                        <div className="glass-panel rounded-2xl p-6">
                            <h2 className="text-sm font-semibold text-th-text-secondary uppercase tracking-wider mb-4">주별 손익 요약</h2>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-white/[0.06]">
                                            <th className="text-left py-3 px-4 text-th-text-muted font-semibold">주차</th>
                                            <th className="text-right py-3 px-4 text-th-text-muted font-semibold">손익</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {performance.weekly_pnl.map((w) => (
                                            <tr key={w.week} className="border-b border-th-border-light hover:bg-th-card transition-colors">
                                                <td className="py-3 px-4 text-th-text">{w.week}</td>
                                                <td className={`py-3 px-4 text-right font-medium ${w.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                    {w.pnl >= 0 ? '+' : ''}{w.pnl.toLocaleString()}원
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </>
            )}
        </PageContainer>
    );
}
