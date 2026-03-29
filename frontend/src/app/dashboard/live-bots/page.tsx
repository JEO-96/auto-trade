'use client';

import { useState, useEffect, useCallback } from 'react';
import { Radio, Users, Bot, Clock } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import Badge from '@/components/ui/Badge';
import { getActiveBots, type ActiveBotPublic } from '@/lib/api/bot';
import { getStrategyLabel, TIMEFRAME_LABEL_MAP, LIVE_BOTS_POLL_INTERVAL_MS } from '@/lib/constants';

export default function LiveBotsPage() {
    const [bots, setBots] = useState<ActiveBotPublic[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchBots = useCallback(async () => {
        try {
            const data = await getActiveBots();
            setBots(data);
        } catch {
            // 실패 시 유지
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchBots();
        const interval = setInterval(fetchBots, LIVE_BOTS_POLL_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [fetchBots]);

    // 통계
    const liveCount = bots.filter(b => !b.paper_trading_mode).length;
    const paperCount = bots.filter(b => b.paper_trading_mode).length;

    // 전략별 그룹핑
    const strategyGroups = bots.reduce<Record<string, ActiveBotPublic[]>>((acc, bot) => {
        const key = bot.strategy_name ?? 'unknown';
        if (!acc[key]) acc[key] = [];
        acc[key].push(bot);
        return acc;
    }, {});

    if (loading) {
        return (
            <PageContainer>
                <div className="flex items-center justify-center py-20">
                    <LoadingSpinner message="실행 중인 봇 불러오는 중..." />
                </div>
            </PageContainer>
        );
    }

    return (
        <PageContainer>
            <header className="mb-6">
                <h1 className="text-2xl font-bold mb-1 text-th-text flex items-center gap-2">
                    <Radio className="w-6 h-6 text-secondary" />
                    실시간 봇 현황
                </h1>
                <p className="text-sm text-th-text-muted">
                    현재 플랫폼에서 실행 중인 모든 모의투자 봇을 확인할 수 있습니다.
                </p>
            </header>

            {/* 요약 카드 */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="glass-panel rounded-2xl p-4 text-center">
                    <p className="text-2xl font-bold text-th-text">{bots.length}</p>
                    <p className="text-xs text-th-text-muted mt-1">전체 실행 중</p>
                </div>
                <div className="glass-panel rounded-2xl p-4 text-center">
                    <p className="text-2xl font-bold text-red-400">{liveCount}</p>
                    <p className="text-xs text-th-text-muted mt-1">실매매</p>
                </div>
                <div className="glass-panel rounded-2xl p-4 text-center">
                    <p className="text-2xl font-bold text-primary">{paperCount}</p>
                    <p className="text-xs text-th-text-muted mt-1">모의투자</p>
                </div>
            </div>

            {bots.length === 0 ? (
                <div className="glass-panel rounded-2xl p-16 text-center">
                    <EmptyState
                        icon={<Bot className="w-12 h-12" />}
                        title="실행 중인 봇이 없습니다"
                        description="아직 아무도 봇을 실행하고 있지 않습니다."
                    />
                </div>
            ) : (
                <div className="space-y-6">
                    {Object.entries(strategyGroups).map(([strategyKey, groupBots]) => (
                        <div key={strategyKey} className="glass-panel rounded-2xl p-5">
                            <div className="flex items-center gap-2 mb-4 min-w-0">
                                <Bot className="w-4 h-4 text-primary shrink-0" />
                                <h3 className="text-sm font-bold text-th-text truncate">
                                    {getStrategyLabel(strategyKey)}
                                </h3>
                                <span className="text-[10px] sm:text-xs text-th-text-muted font-mono truncate hidden sm:inline">
                                    {strategyKey}
                                </span>
                                <Badge variant="default" className="ml-auto">
                                    {groupBots.length}명
                                </Badge>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {groupBots.map((bot, idx) => (
                                    <div
                                        key={`${strategyKey}-${idx}`}
                                        className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-th-border-light"
                                    >
                                        {/* 상태 표시 */}
                                        <div className="relative">
                                            <Users className="w-8 h-8 text-th-text-muted" />
                                            <div className={`absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-background ${
                                                bot.paper_trading_mode ? 'bg-primary' : 'bg-red-400'
                                            }`} />
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold text-th-text truncate">
                                                {bot.nickname ?? '사용자'}
                                            </p>
                                            <div className="flex items-center gap-2 mt-0.5 min-w-0">
                                                <span className="text-[10px] sm:text-xs text-th-text-secondary font-mono truncate">
                                                    {bot.symbol}
                                                </span>
                                                <span className="text-[10px] sm:text-xs text-th-text-muted">|</span>
                                                <span className="text-[10px] sm:text-xs text-th-text-secondary flex items-center gap-0.5">
                                                    <Clock className="w-2.5 h-2.5" />
                                                    {TIMEFRAME_LABEL_MAP[bot.timeframe] ?? bot.timeframe}
                                                </span>
                                            </div>
                                        </div>

                                        <Badge variant={bot.paper_trading_mode ? 'default' : 'danger'}>
                                            {bot.paper_trading_mode ? '모의' : '실매매'}
                                        </Badge>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </PageContainer>
    );
}
