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

export default function TradeLogTimeline({
    tradeLogs,
    selectedBot,
    selectedBotRunning,
}: TradeLogTimelineProps) {
    return (
        <div className="lg:col-span-8">
            <div className="glass-panel p-6 rounded-2xl min-h-[500px] flex flex-col">
                <div className="flex justify-between items-center mb-6 pb-4 border-b border-white/[0.04]">
                    <h3 className="text-base font-bold flex items-center gap-2.5">
                        <BarChart2 className="w-5 h-5 text-secondary" />
                        실행 타임라인
                        {selectedBot && (
                            <span className="text-xs text-gray-500 font-normal ml-2">
                                {selectedBot.symbol}
                            </span>
                        )}
                    </h3>
                    <button
                        aria-label="타임라인 필터"
                        className="flex items-center gap-1.5 text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] px-3 py-2 rounded-lg border border-white/[0.06] transition-colors text-gray-400"
                    >
                        <ListFilter className="w-3.5 h-3.5" />
                        필터
                    </button>
                </div>

                <div className="space-y-3 flex-1 overflow-y-auto">
                    {tradeLogs.length > 0 ? tradeLogs.map((log) => (
                        <div
                            key={log.id}
                            className={`group p-5 rounded-xl border transition-colors ${
                                log.side === TRADE_SIDE.BUY
                                    ? 'bg-primary/[0.03] border-primary/10 hover:border-primary/20'
                                    : 'bg-red-500/[0.03] border-red-500/10 hover:border-red-500/20'
                            }`}
                        >
                            <div className="flex justify-between items-start mb-3">
                                <div className="flex items-center gap-3">
                                    <div className={`p-2 rounded-lg ${
                                        log.side === TRADE_SIDE.BUY
                                            ? 'bg-primary/10 text-primary'
                                            : 'bg-red-500/10 text-red-400'
                                    }`}>
                                        {log.side === TRADE_SIDE.BUY ? <ArrowUpRight className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                    </div>
                                    <div>
                                        <p className={`text-sm font-bold ${log.side === TRADE_SIDE.BUY ? 'text-primary' : 'text-red-400'}`}>
                                            {TRADE_SIDE_LABELS[log.side]}
                                        </p>
                                        <p className="text-[10px] text-gray-500 font-medium">{log.symbol} &middot; {log.timestamp}</p>
                                    </div>
                                </div>
                                {log.pnl != null && (
                                    <div className="text-right">
                                        <p className={`text-base font-bold ${log.pnl > 0 ? 'text-secondary' : 'text-red-400'}`}>
                                            {log.pnl > 0 ? '+' : ''}{formatKRW(Number(log.pnl))}
                                        </p>
                                    </div>
                                )}
                            </div>

                            <div className="flex items-center gap-6 pt-3 border-t border-white/[0.04]">
                                <div>
                                    <p className="text-[10px] text-gray-500 mb-0.5">체결가</p>
                                    <p className="font-mono text-sm text-white font-medium">{formatKRW(Number(log.price ?? 0))}</p>
                                </div>
                                <div>
                                    <p className="text-[10px] text-gray-500 mb-0.5">수량</p>
                                    <p className="font-mono text-sm text-white font-medium">{log.amount}</p>
                                </div>
                                <div className="ml-auto text-right">
                                    <p className="text-[10px] text-gray-500 mb-0.5">트리거</p>
                                    <p className="text-xs text-secondary font-medium">{log.reason}</p>
                                </div>
                            </div>
                        </div>
                    )) : (
                        <EmptyState
                            icon={<Clock className="w-12 h-12" />}
                            title="거래 내역이 없습니다"
                            description={selectedBot ? '이 봇의 거래 내역이 아직 없습니다.' : '봇을 선택하면 거래 타임라인이 표시됩니다.'}
                        />
                    )}

                    {selectedBotRunning && (
                        <div className="flex items-center gap-3 p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                            <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                                <Activity className="w-4 h-4 text-primary animate-pulse" />
                            </div>
                            <div>
                                <p className="text-sm text-white font-medium">실시간 스트리밍 중...</p>
                                <p className="text-[10px] text-gray-500">다음 돌파 패턴을 탐색하고 있습니다</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
