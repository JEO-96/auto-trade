'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Plus, Edit3, AlertTriangle } from 'lucide-react';
import Button from '@/components/ui/Button';
import { SelectInput } from '@/components/ui/Input';
import ModalWrapper, { ModalHeader } from '@/components/ui/ModalWrapper';
import { SYMBOLS, BOT_STRATEGIES, EXCHANGES, getStrategyTimeframe, STRATEGY_TIMEFRAME_TABS, filterStrategiesByTimeframe, TIMEFRAME_LABEL_MAP } from '@/lib/constants';
import { getUserStrategies } from '@/lib/api/strategies';
import type { StrategyItem } from '@/lib/api/settings';
import type { UserStrategy } from '@/types/backtest';

export interface BotFormData {
    symbols: string[];
    timeframe: string;
    exchange_name: string;
    strategy_name: string;
    paper_trading_mode: boolean;
    allocated_capital: number;
    custom_strategy_id?: number;
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
    /** API에서 가져온 전략 목록 (없으면 하드코딩 상수 사용) */
    strategies?: StrategyItem[];
    /** 관리자 여부 (실매매는 관리자만 허용) */
    isAdmin?: boolean;
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
    strategies,
    isAdmin = false,
    onSubmit,
    onClose,
    onFormChange,
}: BotFormModalProps) {
    const liveDisabled = !isAdmin || liveBotLimitReached;
    const displayStrategies = strategies ?? BOT_STRATEGIES.map(s => ({ value: s.value, label: s.label, status: s.status }));

    const [userStrategies, setUserStrategies] = useState<UserStrategy[]>([]);
    useEffect(() => {
        if (isOpen) {
            getUserStrategies().then(setUserStrategies).catch(() => {});
        }
    }, [isOpen]);

    const [tfFilter, setTfFilter] = useState('all');
    const filteredStrategies = useMemo(
        () => filterStrategiesByTimeframe(displayStrategies, tfFilter),
        [displayStrategies, tfFilter],
    );

    // 타임프레임 탭 변경 시 현재 선택된 전략이 필터 목록에 없으면 첫 번째 전략으로 자동 선택
    React.useEffect(() => {
        if (filteredStrategies.length > 0 && !filteredStrategies.some(s => s.value === formData.strategy_name)) {
            const sorted = [
                ...filteredStrategies.filter(s => s.status === 'confirmed'),
                ...filteredStrategies.filter(s => s.status !== 'confirmed'),
            ];
            const first = sorted[0];
            if (first) {
                const newTimeframe = getStrategyTimeframe(first.value);
                onFormChange({ ...formData, strategy_name: first.value, timeframe: newTimeframe });
            }
        }
    }, [filteredStrategies]);

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

                    <SelectInput
                        type="select"
                        label="거래소"
                        value={formData.exchange_name}
                        onChange={(e) => onFormChange({ ...formData, exchange_name: e.target.value })}
                    >
                        {EXCHANGES.map((ex) => (
                            <option key={ex.value} value={ex.value}>{ex.label}</option>
                        ))}
                    </SelectInput>

                    <div>
                        <label className="text-xs text-th-text-muted font-medium mb-2 block">
                            거래 심볼 <span className="text-th-text-muted">&mdash; 복수 선택 가능</span>
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
                                                : 'bg-white/[0.02] border-white/[0.06] text-th-text-muted hover:border-white/10 hover:text-th-text-secondary'
                                        }`}
                                    >
                                        {s.split('/')[0]} <span className="opacity-40 text-[10px] sm:text-xs">/ KRW</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div>
                        <label className="text-xs text-th-text-muted font-medium mb-2 block">전략</label>
                        <div className="flex gap-1 mb-2">
                            {STRATEGY_TIMEFRAME_TABS.map(tab => (
                                <button
                                    key={tab.value}
                                    type="button"
                                    onClick={() => setTfFilter(tab.value)}
                                    className={`px-2.5 py-1 rounded-lg text-[11px] sm:text-xs font-semibold transition-all border ${
                                        tfFilter === tab.value
                                            ? 'bg-primary/10 border-primary/30 text-primary'
                                            : 'bg-white/[0.02] border-white/[0.06] text-th-text-muted hover:text-th-text-secondary'
                                    }`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>
                        <SelectInput
                            type="select"
                            value={formData.custom_strategy_id ? `custom_${formData.custom_strategy_id}` : formData.strategy_name}
                            onChange={(e) => {
                                const val = e.target.value;
                                if (val.startsWith('custom_')) {
                                    const csId = Number(val.replace('custom_', ''));
                                    const cs = userStrategies.find(s => s.id === csId);
                                    if (cs) {
                                        const newTimeframe = getStrategyTimeframe(cs.base_strategy_name);
                                        onFormChange({ ...formData, strategy_name: cs.base_strategy_name, timeframe: newTimeframe, custom_strategy_id: csId });
                                    }
                                } else {
                                    const newTimeframe = getStrategyTimeframe(val);
                                    onFormChange({ ...formData, strategy_name: val, timeframe: newTimeframe, custom_strategy_id: undefined });
                                }
                            }}
                        >
                            {userStrategies.length > 0 && userStrategies.map((cs) => (
                                <option key={`custom_${cs.id}`} value={`custom_${cs.id}`}>
                                    ⭐ {cs.name}
                                </option>
                            ))}
                            {userStrategies.length > 0 && (
                                <option disabled>──────────</option>
                            )}
                            {[
                                ...filteredStrategies.filter(s => s.status === 'confirmed'),
                                ...filteredStrategies.filter(s => s.status !== 'confirmed'),
                            ].map((s) => (
                                <option key={s.value} value={s.value}>
                                    {s.status === 'confirmed' ? `✅ ${s.label}` : `🧪 ${s.label}`}
                                </option>
                            ))}
                        </SelectInput>
                    </div>

                    {/* 캔들 주기 (자동 설정) */}
                    <div>
                        <label className="text-xs text-th-text-muted font-medium mb-1.5 block">캔들 주기</label>
                        <div className="bg-white/[0.02] border border-th-border-light rounded-xl px-4 py-3 flex items-center gap-2">
                            <span className="text-sm font-semibold text-primary">{TIMEFRAME_LABEL_MAP[formData.timeframe] || formData.timeframe}</span>
                            <span className="text-[10px] sm:text-xs text-th-text-muted">(전략에 의해 자동 설정)</span>
                        </div>
                    </div>

                    {/* Trading mode toggle */}
                    <div>
                        <label className="text-xs text-th-text-muted font-medium mb-2 block">매매 모드</label>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                type="button"
                                onClick={() => onFormChange({ ...formData, paper_trading_mode: true })}
                                className={`py-3 rounded-xl text-sm font-semibold transition-all border ${
                                    formData.paper_trading_mode
                                        ? 'bg-primary/10 border-primary/30 text-primary'
                                        : 'bg-white/[0.02] border-white/[0.06] text-th-text-muted hover:border-white/10'
                                }`}
                            >
                                모의투자
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    if (!liveDisabled) {
                                        onFormChange({ ...formData, paper_trading_mode: false });
                                    }
                                }}
                                disabled={liveDisabled}
                                className={`py-3 rounded-xl text-sm font-semibold transition-all border ${
                                    !formData.paper_trading_mode
                                        ? 'bg-red-500/10 border-red-500/30 text-red-400'
                                        : liveDisabled
                                            ? 'bg-white/[0.02] border-th-border-light text-th-text-muted cursor-not-allowed'
                                            : 'bg-white/[0.02] border-white/[0.06] text-th-text-muted hover:border-white/10'
                                }`}
                            >
                                실매매 {!isAdmin && <span className="text-[10px] sm:text-xs opacity-60">(준비중)</span>}
                            </button>
                        </div>
                        {!isAdmin && formData.paper_trading_mode && (
                            <div className="mt-3 flex items-start gap-2.5 p-3 bg-blue-500/[0.06] rounded-xl border border-blue-500/15">
                                <AlertTriangle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                                <p className="text-xs text-blue-400/90 leading-relaxed">
                                    실매매 기능은 현재 준비 중입니다. 모의투자 모드로 전략을 테스트해보세요.
                                </p>
                            </div>
                        )}
                        {isAdmin && liveBotLimitReached && formData.paper_trading_mode && (
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
                        <label className="text-xs text-th-text-muted font-medium mb-1.5 block">
                            운용 자본 (KRW)
                            {!formData.paper_trading_mode && availableKrw !== undefined && (
                                <span className="ml-2 text-th-text-muted">
                                    보유 현금: {Math.floor(availableKrw).toLocaleString()}원
                                </span>
                            )}
                        </label>
                        <div className="relative">
                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-th-text-muted font-semibold text-sm">&#8361;</div>
                            <input
                                type="text"
                                inputMode="numeric"
                                value={Number(formData.allocated_capital ?? 0).toLocaleString()}
                                onChange={(e) => {
                                    const val = e.target.value.replace(/[^0-9]/g, '');
                                    onFormChange({ ...formData, allocated_capital: val ? Number(val) : 0 });
                                }}
                                className={`w-full bg-white/[0.02] border rounded-xl pl-10 pr-4 py-3 text-sm font-bold text-th-text focus:border-primary/30 transition-colors font-mono ${
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
