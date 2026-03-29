'use client';

import {
    BarChart2, ListFilter, ArrowUpRight, TrendingDown, Clock, Activity,
} from 'lucide-react';
import EmptyState from '@/components/ui/EmptyState';
import { TRADE_SIDE, TRADE_SIDE_LABELS } from '@/lib/constants';
import { formatKRW } from '@/lib/utils';
import type { BotConfig, TradeLog } from '@/types/bot';

export interface TradeLogTimelineProps {
    tradeLogs: TradeLog[];
    selectedBot: BotConfig | null;
    selectedBotRunning: boolean;
}

function formatAmount(amount: string | number): string {
    const num = Number(amount);
    if (isNaN(num)) return String(amount);
    if (num >= 1) return num.toFixed(4);
    return num.toFixed(6);
}

export default function TradeLogTimeline({
    tradeLogs,
    selectedBot,
    selectedBotRunning,
}: TradeLogTimelineProps) {
    return (
        <div className="lg:col-span-8">
            <div className="glass-panel p-4 sm:p-6 rounded-2xl min-h-[500px] flex flex-col opacity-0 animate-scale-in">
                {/* Header */}
                <div className="flex justify-between items-center gap-2 mb-6 pb-4 border-b border-th-border-light">
                    <h3 className="text-base font-bold text-th-text flex items-center gap-2 min-w-0">
                        <BarChart2 className="w-5 h-5 text-secondary shrink-0" />
                        <span className="shrink-0">실행 타임라인</span>
                        {selectedBot && (
                            <span className="text-xs text-th-text-muted font-normal truncate max-w-[120px] sm:max-w-[200px]">
                                {selectedBot.symbol}
                            </span>
                        )}
                    </h3>
                    <button
                        aria-label="타임라인 필터"
                        className="flex items-center gap-1.5 text-xs font-medium bg-th-card hover:bg-th-hover px-3 py-2 rounded-lg border border-th-border transition-colors text-th-text-secondary shrink-0"
                    >
                        <ListFilter className="w-3.5 h-3.5" />
                        필터
                    </button>
                </div>

                {/* Trade Log List */}
                <div className="space-y-3 flex-1 overflow-y-auto">
                    {tradeLogs.length > 0 ? tradeLogs.map((log, idx) => (
                        <div
                            key={log.id}
                            style={{ animationDelay: `${Math.min(idx, 8) * 60}ms` }}
                            className={`group p-4 sm:p-5 rounded-xl border transition-colors overflow-hidden opacity-0 animate-fade-in-up ${
                                log.side === TRADE_SIDE.BUY
                                    ? 'bg-primary/[0.03] border-primary/10 hover:border-primary/20'
                                    : 'bg-red-500/[0.03] border-red-500/10 hover:border-red-500/20'
                            }`}
                        >
                            {/* Top: Side label + PnL */}
                            <div className="flex justify-between items-start gap-2 mb-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className={`p-2 rounded-lg shrink-0 ${
                                        log.side === TRADE_SIDE.BUY
                                            ? 'bg-primary/10 text-primary'
                                            : 'bg-red-500/10 text-red-400'
                                    }`}>
                                        {log.side === TRADE_SIDE.BUY ? <ArrowUpRight className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                    </div>
                                    <div className="min-w-0">
                                        <p className={`text-sm font-bold ${log.side === TRADE_SIDE.BUY ? 'text-primary' : 'text-red-400'}`}>
                                            {TRADE_SIDE_LABELS[log.side]}
                                        </p>
                                        <p className="text-[10px] sm:text-xs text-th-text-muted font-medium truncate">
                                            {log.symbol} &middot; {log.timestamp}
                                        </p>
                                    </div>
                                </div>
                                {log.pnl != null && (
                                    <div className="text-right shrink-0">
                                        <p className={`text-sm sm:text-base font-bold ${Number(log.pnl) > 0 ? 'text-secondary' : 'text-red-400'}`}>
                                            {Number(log.pnl) > 0 ? '+' : ''}{formatKRW(Number(log.pnl))}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Bottom: Details grid */}
                            <div className="grid grid-cols-3 gap-2 sm:gap-4 pt-3 border-t border-th-border-light">
                                <div className="min-w-0">
                                    <p className="text-[10px] sm:text-xs text-th-text-muted mb-0.5">체결가</p>
                                    <p className="font-mono text-xs sm:text-sm text-th-text font-medium truncate">
                                        {formatKRW(Number(log.price ?? 0))}
                                    </p>
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[10px] sm:text-xs text-th-text-muted mb-0.5">수량</p>
                                    <p className="font-mono text-xs sm:text-sm text-th-text font-medium truncate">
                                        {formatAmount(log.amount)}
                                    </p>
                                </div>
                                <div className="min-w-0 text-right">
                                    <p className="text-[10px] sm:text-xs text-th-text-muted mb-0.5">트리거</p>
                                    <p className="text-xs text-secondary font-medium truncate">
                                        {log.reason}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )) : (
                        <EmptyState
                            icon={<Clock className="w-12 h-12" />}
                            title="아직 거래가 없어요"
                            description={selectedBot ? '봇이 시장을 분석하고 있어요. 조건이 맞으면 자동으로 거래합니다.' : '왼쪽에서 봇을 선택하면 거래 기록이 여기에 표시돼요.'}
                        />
                    )}

                    {selectedBotRunning && (
                        <div className="flex items-center gap-3 p-4 bg-th-card rounded-xl border border-th-border-light">
                            <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center shrink-0">
                                <Activity className="w-4 h-4 text-primary animate-live-dot" />
                            </div>
                            <div className="min-w-0">
                                <p className="text-sm text-th-text font-medium">실시간 스트리밍 중...</p>
                                <p className="text-[10px] sm:text-xs text-th-text-muted truncate">다음 돌파 패턴을 탐색하고 있습니다</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
