'use client';

import {
    Play, StopCircle, Edit3, Trash2,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { BOT_MODE_LABELS } from '@/lib/constants';
import { formatKRW } from '@/lib/utils';
import type { BotConfig } from '@/types/bot';

export interface BotCardProps {
    bot: BotConfig;
    isRunning: boolean;
    isSelected: boolean;
    isActionLoading: boolean;
    strategyLabelMap: Record<string, string>;
    timeframeLabelMap: Record<string, string>;
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
    strategyLabelMap,
    timeframeLabelMap,
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
            className={`glass-panel p-5 rounded-2xl cursor-pointer transition-all border-2 ${
                isSelected
                    ? 'border-primary/30 bg-primary/[0.03]'
                    : 'border-transparent hover:border-white/[0.06]'
            }`}
        >
            {/* Top row: symbol + status */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                    <div className={`w-2.5 h-2.5 rounded-full ${
                        isRunning
                            ? 'bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                            : 'bg-gray-600'
                    }`}></div>
                    <span className="text-base font-bold text-white">{bot.symbol}</span>
                </div>
                <div className="flex items-center gap-1.5">
                    {bot.paper_trading_mode ? (
                        <Badge variant="info">{BOT_MODE_LABELS.paper}</Badge>
                    ) : (
                        <Badge variant="danger">{BOT_MODE_LABELS.live}</Badge>
                    )}
                    <Badge variant={isRunning ? 'success' : 'warning'}>
                        {isRunning ? '가동중' : '정지'}
                    </Badge>
                </div>
            </div>

            {/* Bot details */}
            <div className="flex items-center gap-4 text-[11px] text-gray-500 mb-4">
                <span>{strategyLabelMap[bot.strategy_name] ?? bot.strategy_name}</span>
                <span>{timeframeLabelMap[bot.timeframe] ?? bot.timeframe}</span>
            </div>

            <div className="flex items-center justify-between mb-4">
                <div>
                    <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">운용 자본</p>
                    <p className="text-sm font-semibold text-white font-mono">{formatKRW(bot.allocated_capital ?? 0)}</p>
                </div>
                <div className="text-right">
                    <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">RSI / Vol MA</p>
                    <p className="text-sm font-semibold text-white font-mono">{bot.rsi_period} / {bot.volume_ma_period}</p>
                </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 pt-3 border-t border-white/[0.04]" onClick={(e) => e.stopPropagation()}>
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
