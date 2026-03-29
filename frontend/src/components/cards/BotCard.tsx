'use client';

import {
    Play, StopCircle, Edit3, Trash2,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { BOT_MODE_LABELS, getStrategyLabel, TIMEFRAME_LABEL_MAP } from '@/lib/constants';
import { formatKRW } from '@/lib/utils';
import type { BotConfig } from '@/types/bot';

export interface BotCardProps {
    bot: BotConfig;
    isRunning: boolean;
    isSelected: boolean;
    isActionLoading: boolean;
    index?: number;
    onSelect: (botId: number) => void;
    onStart: (botId: number) => void;
    onStop: (botId: number) => void;
    onEdit: (bot: BotConfig) => void;
    onDelete: (botId: number) => void;
}

export default function BotCard({
    bot,
    isRunning,
    isSelected,
    isActionLoading,
    index = 0,
    onSelect,
    onStart,
    onStop,
    onEdit,
    onDelete,
}: BotCardProps) {
    return (
        <div
            onClick={() => onSelect(bot.id)}
            role="button"
            tabIndex={0}
            aria-label={`${bot.symbol} 봇 선택`}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(bot.id); }}
            style={{ animationDelay: `${index * 80}ms` }}
            className={`glass-panel p-5 rounded-2xl cursor-pointer transition-all border-2 overflow-hidden opacity-0 animate-slide-in-left ${
                !bot.paper_trading_mode && isRunning
                    ? isSelected
                        ? 'border-red-500/40 bg-red-500/[0.03]'
                        : 'border-red-500/20 hover:border-red-500/30'
                    : isSelected
                        ? 'border-primary/30 bg-primary/[0.03]'
                        : 'border-transparent hover:border-th-border-light'
            }`}
        >
            {/* Top row: symbol + status */}
            <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-start gap-2.5 min-w-0 flex-1">
                    <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${
                        isRunning
                            ? 'bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-live-dot'
                            : 'bg-th-text-muted/40'
                    }`}></div>
                    <div className="min-w-0">
                        {(() => {
                            const symbols = bot.symbol.split(',').map(s => s.trim()).filter(Boolean);
                            if (symbols.length <= 2) {
                                return <span className="text-base font-bold text-th-text break-all">{bot.symbol}</span>;
                            }
                            return (
                                <div className="flex flex-wrap gap-1">
                                    {symbols.map((sym) => (
                                        <span key={sym} className="text-xs font-bold text-th-text bg-th-card px-1.5 py-0.5 rounded">
                                            {sym.replace('/KRW', '')}
                                        </span>
                                    ))}
                                </div>
                            );
                        })()}
                    </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                    {bot.paper_trading_mode ? (
                        <Badge variant="info">{BOT_MODE_LABELS.paper}</Badge>
                    ) : (
                        <Badge variant="danger">
                            {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />}
                            {BOT_MODE_LABELS.live}
                        </Badge>
                    )}
                    <Badge variant={isRunning ? 'success' : 'warning'}>
                        {isRunning ? '가동중' : '정지'}
                    </Badge>
                </div>
            </div>

            {/* Bot details */}
            <div className="flex items-center gap-4 text-[11px] sm:text-xs text-th-text-muted mb-4">
                <span className="uppercase font-semibold text-[10px] sm:text-xs bg-th-card px-1.5 py-0.5 rounded">
                    {bot.exchange_name || 'upbit'}
                </span>
                <span>{getStrategyLabel(bot.strategy_name)}</span>
                <span>{TIMEFRAME_LABEL_MAP[bot.timeframe] ?? bot.timeframe}</span>
            </div>

            <div className="flex items-center justify-between mb-4">
                <div>
                    <p className="text-[10px] sm:text-xs text-th-text-muted font-medium uppercase tracking-wider mb-0.5">운용 자본</p>
                    <p className="text-sm font-semibold text-th-text font-mono">
                        {bot.paper_trading_mode ? formatKRW(bot.allocated_capital ?? 0) : '잔고 100%'}
                    </p>
                </div>
                <div className="text-right">
                    <p className="text-[10px] sm:text-xs text-th-text-muted font-medium uppercase tracking-wider mb-0.5">RSI / Vol MA</p>
                    <p className="text-sm font-semibold text-th-text font-mono">{bot.rsi_period} / {bot.volume_ma_period}</p>
                </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 pt-3 border-t border-th-border-light" onClick={(e) => e.stopPropagation()}>
                {isRunning ? (
                    <Button
                        variant="danger"
                        size="sm"
                        className="flex-1"
                        onClick={() => onStop(bot.id)}
                        loading={isActionLoading}
                    >
                        <StopCircle className="w-3.5 h-3.5" />
                        정지
                    </Button>
                ) : (
                    <>
                        <Button
                            variant="primary"
                            size="sm"
                            className="flex-1"
                            onClick={() => onStart(bot.id)}
                            loading={isActionLoading}
                        >
                            <Play className="w-3.5 h-3.5" />
                            가동
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onEdit(bot)}
                            aria-label="봇 설정"
                        >
                            <Edit3 className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onDelete(bot.id)}
                            aria-label="봇 삭제"
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/[0.06]"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
}
