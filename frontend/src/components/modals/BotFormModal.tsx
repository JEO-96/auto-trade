'use client';

import { useMemo } from 'react';
import { Plus, Edit3, AlertTriangle } from 'lucide-react';
import Button from '@/components/ui/Button';
import { SelectInput } from '@/components/ui/Input';
import ModalWrapper, { ModalHeader } from '@/components/ui/ModalWrapper';
import { SYMBOLS, BOT_STRATEGIES, BOT_TIMEFRAMES, BOT_TO_BACKTEST_STRATEGY } from '@/lib/constants';
import type { StrategyItem } from '@/lib/api/settings';

export interface BotFormData {
    symbols: string[];
    timeframe: string;
    strategy_name: string;
    paper_trading_mode: boolean;
    allocated_capital: number;
}

export interface BotFormModalProps {
    isOpen: boolean;
    mode: 'create' | 'edit';
    formData: BotFormData;
    formError: string | null;
    formLoading: boolean;
    liveBotLimitReached: boolean;
    /** 업비트 보유 KRW 현금 잔고 (실매매 자본 상한) */
    availableKrw?: number;
    /** 전략별 허용 타임프레임 매핑 (backtest 전략 키 기준) */
    strategyTimeframeMap?: Record<string, string[]>;
    /** API에서 가져온 전략 목록 (없으면 하드코딩 상수 사용) */
    strategies?: StrategyItem[];
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
    onFormChange: (data: BotFormData) => void;
}

export default function BotFormModal({
    isOpen,
    mode,
    formData,
    formError,
    formLoading,
    liveBotLimitReached,
    availableKrw,
    strategyTimeframeMap,
    strategies,
    onSubmit,
    onClose,
    onFormChange,
}: BotFormModalProps) {
    const displayStrategies = strategies ?? BOT_STRATEGIES.map(s => ({ value: s.value, label: s.label }));
    // 현재 선택된 봇 전략에 허용된 타임프레임 필터링
    const filteredTimeframes = useMemo(() => {
        if (!strategyTimeframeMap) return [...BOT_TIMEFRAMES];
        const backtestKey = BOT_TO_BACKTEST_STRATEGY[formData.strategy_name] ?? formData.strategy_name;
        const allowed = strategyTimeframeMap[backtestKey];
        if (!allowed || allowed.length === 0) return [...BOT_TIMEFRAMES];
        return BOT_TIMEFRAMES.filter(tf => allowed.includes(tf.value));
    }, [strategyTimeframeMap, formData.strategy_name]);

    return (
        <ModalWrapper isOpen={isOpen}>
                <ModalHeader
                    icon={<div className="w-9 h-9 bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">{mode === 'create' ? <Plus className="w-5 h-5 text-primary" /> : <Edit3 className="w-5 h-5 text-primary" />}</div>}
                    title={mode === 'create' ? '새 봇 만들기' : '봇 설정 수정'}
                    onClose={onClose}
                />

                <form onSubmit={onSubmit} className="p-6 space-y-5">
                    {formError && (
                        <div className="p-3 rounded-xl bg-red-500/[0.06] border border-red-500/20 text-red-400 text-sm">
                            {formError}
                        </div>
                    )}

                    <div>
                        <label className="text-xs text-gray-500 font-medium mb-2 block">
                            심볼 (Symbol) <span className="text-gray-600">&mdash; 복수 선택 가능</span>
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                            {SYMBOLS.map(s => {
                                const isSelected = formData.symbols.includes(s);
                                return (
                                    <button
                                        key={s}
                                        type="button"
                                        onClick={() => {
                                            onFormChange({
                                                ...formData,
                                                symbols: isSelected
                                                    ? formData.symbols.filter(sym => sym !== s)
                                                    : [...formData.symbols, s],
                                            });
                                        }}
                                        className={`py-2.5 rounded-xl text-xs font-semibold transition-all border ${
                                            isSelected
                                                ? 'bg-primary/10 border-primary/30 text-primary'
                                                : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10 hover:text-gray-300'
                                        }`}
                                    >
                                        {s.split('/')[0]} <span className="opacity-40 text-[10px]">/ KRW</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <SelectInput
                        type="select"
                        label="전략 (Strategy)"
                        value={formData.strategy_name}
                        onChange={(e) => {
                            const newStrategy = e.target.value;
                            // 전략 변경 시 타임프레임이 허용 범위 밖이면 자동 조정
                            let newTimeframe = formData.timeframe;
                            if (strategyTimeframeMap) {
                                const bKey = BOT_TO_BACKTEST_STRATEGY[newStrategy] ?? newStrategy;
                                const allowed = strategyTimeframeMap[bKey];
                                if (allowed && allowed.length > 0 && !allowed.includes(newTimeframe)) {
                                    newTimeframe = allowed[0];
                                }
                            }
                            onFormChange({ ...formData, strategy_name: newStrategy, timeframe: newTimeframe });
                        }}
                    >
                        {displayStrategies.map((s) => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                    </SelectInput>

                    <SelectInput
                        type="select"
                        label="캔들 주기 (Timeframe)"
                        value={formData.timeframe}
                        onChange={(e) => onFormChange({ ...formData, timeframe: e.target.value })}
                    >
                        {filteredTimeframes.map((tf) => (
                            <option key={tf.value} value={tf.value}>{tf.label}</option>
                        ))}
                    </SelectInput>

                    {/* Trading mode toggle */}
                    <div>
                        <label className="text-xs text-gray-500 font-medium mb-2 block">매매 모드</label>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                type="button"
                                onClick={() => onFormChange({ ...formData, paper_trading_mode: true })}
                                className={`py-3 rounded-xl text-sm font-semibold transition-all border ${
                                    formData.paper_trading_mode
                                        ? 'bg-primary/10 border-primary/30 text-primary'
                                        : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10'
                                }`}
                            >
                                모의투자
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    if (!liveBotLimitReached) {
                                        onFormChange({ ...formData, paper_trading_mode: false });
                                    }
                                }}
                                disabled={liveBotLimitReached}
                                className={`py-3 rounded-xl text-sm font-semibold transition-all border ${
                                    !formData.paper_trading_mode
                                        ? 'bg-red-500/10 border-red-500/30 text-red-400'
                                        : liveBotLimitReached
                                            ? 'bg-white/[0.01] border-white/[0.04] text-gray-700 cursor-not-allowed'
                                            : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10'
                                }`}
                            >
                                실매매
                            </button>
                        </div>
                        {liveBotLimitReached && formData.paper_trading_mode && (
                            <div className="mt-3 flex items-start gap-2.5 p-3 bg-yellow-500/[0.06] rounded-xl border border-yellow-500/15">
                                <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
                                <p className="text-xs text-yellow-400/90 leading-relaxed">
                                    실매매 봇은 1개만 운영할 수 있습니다. 기존 실매매 봇을 삭제하거나 모의투자로 전환하세요.
                                </p>
                            </div>
                        )}
                        {!formData.paper_trading_mode && (
                            <div className="mt-3 flex items-start gap-2.5 p-3 bg-red-500/[0.06] rounded-xl border border-red-500/15">
                                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                                <p className="text-xs text-red-400/90 leading-relaxed">
                                    실매매 모드에서는 실제 자금이 거래됩니다.
                                    원금 손실 위험이 있으니 신중하게 설정하세요.
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Capital */}
                    <div>
                        <label className="text-xs text-gray-500 font-medium mb-1.5 block">
                            운용 자본 (KRW)
                            {!formData.paper_trading_mode && availableKrw !== undefined && (
                                <span className="ml-2 text-gray-600">
                                    보유 현금: {Math.floor(availableKrw).toLocaleString()}원
                                </span>
                            )}
                        </label>
                        <div className="relative">
                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-semibold text-sm">&#8361;</div>
                            <input
                                type="text"
                                inputMode="numeric"
                                value={Number(formData.allocated_capital ?? 0).toLocaleString()}
                                onChange={(e) => {
                                    const val = e.target.value.replace(/[^0-9]/g, '');
                                    onFormChange({ ...formData, allocated_capital: val ? Number(val) : 0 });
                                }}
                                className={`w-full bg-white/[0.03] border rounded-xl pl-10 pr-4 py-3 text-sm font-bold text-white focus:border-primary/30 transition-colors font-mono ${
                                    !formData.paper_trading_mode && availableKrw !== undefined && formData.allocated_capital > Math.floor(availableKrw)
                                        ? 'border-red-500/40'
                                        : 'border-white/[0.06]'
                                }`}
                                placeholder="0"
                            />
                        </div>
                        {!formData.paper_trading_mode && availableKrw !== undefined && formData.allocated_capital > Math.floor(availableKrw) && (
                            <p className="mt-1.5 text-xs text-red-400">
                                보유 현금({Math.floor(availableKrw).toLocaleString()}원)보다 큰 금액은 입력할 수 없습니다.
                            </p>
                        )}
                    </div>

                    <div className="flex gap-3 pt-2">
                        <Button
                            variant="ghost"
                            size="md"
                            className="flex-1"
                            type="button"
                            onClick={onClose}
                            disabled={formLoading}
                        >
                            취소
                        </Button>
                        <Button
                            variant="primary"
                            size="md"
                            className="flex-1"
                            type="submit"
                            loading={formLoading}
                            disabled={!formData.paper_trading_mode && availableKrw !== undefined && formData.allocated_capital > Math.floor(availableKrw)}
                        >
                            {mode === 'create' ? '생성' : '저장'}
                        </Button>
                    </div>
                </form>
        </ModalWrapper>
    );
}
