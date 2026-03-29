'use client';
import React from 'react';
import { Settings } from 'lucide-react';

export interface TuningState {
    enabled: boolean;
    trailing: boolean;
    sl: number;
    tp: number;
    rsiPeriod: number;
    rsiThreshold: number;
    adxThreshold: number;
    volMultiplier: number;
    macdFast: number;
    macdSlow: number;
    macdSignal: number;
    rsiUpperLimit: number;
    atrPeriod: number;
    useRsiFilter: boolean;
    useAdxFilter: boolean;
    useVolumeFilter: boolean;
    useMacdFilter: boolean;
}

export const DEFAULT_TUNING_STATE: TuningState = {
    enabled: false,
    trailing: false,
    sl: 1.5,
    tp: 3.0,
    rsiPeriod: 14,
    rsiThreshold: 60,
    adxThreshold: 20,
    volMultiplier: 1.5,
    macdFast: 12,
    macdSlow: 26,
    macdSignal: 9,
    rsiUpperLimit: 78,
    atrPeriod: 14,
    useRsiFilter: true,
    useAdxFilter: true,
    useVolumeFilter: true,
    useMacdFilter: true,
};

interface ParameterTuningPanelProps {
    state: TuningState;
    onChange: (patch: Partial<TuningState>) => void;
    onSyncDefaults: (strategyName: string) => void;
    strategyName: string;
}

export default function ParameterTuningPanel({ state, onChange, onSyncDefaults, strategyName }: ParameterTuningPanelProps) {
    const {
        enabled, trailing, sl, tp,
        rsiPeriod, rsiThreshold, rsiUpperLimit,
        macdFast, macdSlow, macdSignal,
        adxThreshold, volMultiplier, atrPeriod,
        useRsiFilter, useAdxFilter, useVolumeFilter, useMacdFilter,
    } = state;

    return (
        <div className="border border-white/[0.06] rounded-xl overflow-hidden">
            <button
                type="button"
                onClick={() => {
                    if (!enabled) onSyncDefaults(strategyName);
                    onChange({ enabled: !enabled });
                }}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
            >
                <span className="flex items-center gap-2 text-xs font-semibold text-gray-400">
                    <Settings className="w-3.5 h-3.5" />
                    파라미터 튜닝
                </span>
                <div className={`w-8 h-4.5 rounded-full transition-colors relative ${enabled ? 'bg-primary' : 'bg-white/10'}`}>
                    <div className={`absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white shadow transition-transform ${enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </div>
            </button>
            {enabled && (
                <div className="px-4 pb-4 pt-2 space-y-4 border-t border-white/[0.06]">
                    {/* 청산 모드 */}
                    <div>
                        <label className="text-[10px] sm:text-xs text-gray-500 font-medium mb-2 block uppercase tracking-wider">청산 모드</label>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                type="button"
                                onClick={() => onChange({ trailing: false })}
                                className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${!trailing ? 'bg-primary/15 text-primary border border-primary/30' : 'bg-white/[0.02] text-gray-500 border border-white/[0.06] hover:text-white'}`}
                            >
                                고정 SL/TP
                            </button>
                            <button
                                type="button"
                                onClick={() => onChange({ trailing: true })}
                                className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${trailing ? 'bg-primary/15 text-primary border border-primary/30' : 'bg-white/[0.02] text-gray-500 border border-white/[0.06] hover:text-white'}`}
                            >
                                트레일링 스탑
                            </button>
                        </div>
                    </div>

                    {/* 손절률 */}
                    <div>
                        <div className="flex items-center justify-between mb-1.5">
                            <label className="text-[10px] sm:text-xs text-gray-500 font-medium uppercase tracking-wider">
                                {trailing ? '트레일링 스탑' : '손절률 (SL)'}
                            </label>
                            <span className="text-xs font-bold text-red-400 font-mono">{sl.toFixed(1)}%</span>
                        </div>
                        <input
                            type="range"
                            min="0.5"
                            max="10"
                            step="0.5"
                            value={sl}
                            onChange={(e) => onChange({ sl: Number(e.target.value) })}
                            className="w-full h-1.5 rounded-full appearance-none bg-white/10 accent-red-400 cursor-pointer"
                        />
                        <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
                            <span>0.5%</span>
                            <span>10%</span>
                        </div>
                    </div>

                    {/* 익절률 (트레일링 아닐 때만) */}
                    {!trailing && (
                        <div>
                            <div className="flex items-center justify-between mb-1.5">
                                <label className="text-[10px] sm:text-xs text-gray-500 font-medium uppercase tracking-wider">익절률 (TP)</label>
                                <span className="text-xs font-bold text-emerald-400 font-mono">{tp.toFixed(1)}%</span>
                            </div>
                            <input
                                type="range"
                                min="1"
                                max="50"
                                step="1"
                                value={tp}
                                onChange={(e) => onChange({ tp: Number(e.target.value) })}
                                className="w-full h-1.5 rounded-full appearance-none bg-white/10 accent-emerald-400 cursor-pointer"
                            />
                            <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
                                <span>1%</span>
                                <span>50%</span>
                            </div>
                        </div>
                    )}

                    {trailing && (
                        <p className="text-[10px] sm:text-xs text-gray-500 bg-white/[0.02] rounded-lg px-3 py-2">
                            트레일링 모드: 최고가 대비 {sl.toFixed(1)}% 하락 시 청산. 익절 목표 없이 추세를 끝까지 추종합니다.
                        </p>
                    )}

                    {/* 진입 신호 조건 설정 */}
                    <div className="pt-3 border-t border-white/[0.06] space-y-3">
                        <label className="text-[10px] sm:text-xs text-gray-500 font-medium block uppercase tracking-wider">진입 조건 설정</label>

                        {/* RSI 필터 */}
                        <div className={`rounded-lg border transition-colors ${useRsiFilter ? 'border-blue-500/20 bg-blue-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                            <button type="button" onClick={() => onChange({ useRsiFilter: !useRsiFilter })}
                                className="w-full flex items-center justify-between px-3 py-2">
                                <span className={`text-[11px] sm:text-xs font-semibold ${useRsiFilter ? 'text-blue-400' : 'text-gray-600'}`}>RSI 필터</span>
                                <div className={`w-7 h-4 rounded-full transition-colors relative ${useRsiFilter ? 'bg-blue-500' : 'bg-white/10'}`}>
                                    <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useRsiFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                </div>
                            </button>
                            {useRsiFilter && (
                                <div className="px-3 pb-2.5 space-y-2">
                                    <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">기간</span><span className="text-[10px] sm:text-xs font-bold text-blue-400 font-mono">{rsiPeriod}</span></div>
                                        <input type="range" min="7" max="30" step="1" value={rsiPeriod} onChange={(e) => onChange({ rsiPeriod: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-blue-400 cursor-pointer" /></div>
                                    <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">진입 기준</span><span className="text-[10px] sm:text-xs font-bold text-blue-400 font-mono">{rsiThreshold}</span></div>
                                        <input type="range" min="30" max="80" step="1" value={rsiThreshold} onChange={(e) => onChange({ rsiThreshold: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-blue-400 cursor-pointer" /></div>
                                    <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">과매수 상한</span><span className="text-[10px] sm:text-xs font-bold text-blue-400 font-mono">{rsiUpperLimit}</span></div>
                                        <input type="range" min="65" max="95" step="1" value={rsiUpperLimit} onChange={(e) => onChange({ rsiUpperLimit: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-blue-400 cursor-pointer" /></div>
                                </div>
                            )}
                        </div>

                        {/* MACD 필터 */}
                        <div className={`rounded-lg border transition-colors ${useMacdFilter ? 'border-cyan-500/20 bg-cyan-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                            <button type="button" onClick={() => onChange({ useMacdFilter: !useMacdFilter })}
                                className="w-full flex items-center justify-between px-3 py-2">
                                <span className={`text-[11px] sm:text-xs font-semibold ${useMacdFilter ? 'text-cyan-400' : 'text-gray-600'}`}>MACD 필터</span>
                                <div className={`w-7 h-4 rounded-full transition-colors relative ${useMacdFilter ? 'bg-cyan-500' : 'bg-white/10'}`}>
                                    <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useMacdFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                </div>
                            </button>
                            {useMacdFilter && (
                                <div className="px-3 pb-2.5 space-y-2">
                                    <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">단기 (Fast)</span><span className="text-[10px] sm:text-xs font-bold text-cyan-400 font-mono">{macdFast}</span></div>
                                        <input type="range" min="5" max="20" step="1" value={macdFast} onChange={(e) => onChange({ macdFast: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-cyan-400 cursor-pointer" /></div>
                                    <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">장기 (Slow)</span><span className="text-[10px] sm:text-xs font-bold text-cyan-400 font-mono">{macdSlow}</span></div>
                                        <input type="range" min="15" max="40" step="1" value={macdSlow} onChange={(e) => onChange({ macdSlow: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-cyan-400 cursor-pointer" /></div>
                                    <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">시그널</span><span className="text-[10px] sm:text-xs font-bold text-cyan-400 font-mono">{macdSignal}</span></div>
                                        <input type="range" min="3" max="15" step="1" value={macdSignal} onChange={(e) => onChange({ macdSignal: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-cyan-400 cursor-pointer" /></div>
                                </div>
                            )}
                        </div>

                        {/* ADX 필터 */}
                        <div className={`rounded-lg border transition-colors ${useAdxFilter ? 'border-purple-500/20 bg-purple-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                            <button type="button" onClick={() => onChange({ useAdxFilter: !useAdxFilter })}
                                className="w-full flex items-center justify-between px-3 py-2">
                                <span className={`text-[11px] sm:text-xs font-semibold ${useAdxFilter ? 'text-purple-400' : 'text-gray-600'}`}>ADX 추세 필터</span>
                                <div className={`w-7 h-4 rounded-full transition-colors relative ${useAdxFilter ? 'bg-purple-500' : 'bg-white/10'}`}>
                                    <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useAdxFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                </div>
                            </button>
                            {useAdxFilter && (
                                <div className="px-3 pb-2.5">
                                    <div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">추세 강도 기준</span><span className="text-[10px] sm:text-xs font-bold text-purple-400 font-mono">{adxThreshold}</span></div>
                                    <input type="range" min="10" max="40" step="1" value={adxThreshold} onChange={(e) => onChange({ adxThreshold: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-purple-400 cursor-pointer" />
                                </div>
                            )}
                        </div>

                        {/* 거래량 필터 */}
                        <div className={`rounded-lg border transition-colors ${useVolumeFilter ? 'border-amber-500/20 bg-amber-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                            <button type="button" onClick={() => onChange({ useVolumeFilter: !useVolumeFilter })}
                                className="w-full flex items-center justify-between px-3 py-2">
                                <span className={`text-[11px] sm:text-xs font-semibold ${useVolumeFilter ? 'text-amber-400' : 'text-gray-600'}`}>거래량 필터</span>
                                <div className={`w-7 h-4 rounded-full transition-colors relative ${useVolumeFilter ? 'bg-amber-500' : 'bg-white/10'}`}>
                                    <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useVolumeFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                </div>
                            </button>
                            {useVolumeFilter && (
                                <div className="px-3 pb-2.5">
                                    <div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">평균 대비 배수</span><span className="text-[10px] sm:text-xs font-bold text-amber-400 font-mono">{volMultiplier.toFixed(1)}x</span></div>
                                    <input type="range" min="0.5" max="3.0" step="0.1" value={volMultiplier} onChange={(e) => onChange({ volMultiplier: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-amber-400 cursor-pointer" />
                                </div>
                            )}
                        </div>

                        {/* ATR 기간 */}
                        <div className="px-1">
                            <div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">ATR 변동성 기간</span><span className="text-[10px] sm:text-xs font-bold text-gray-400 font-mono">{atrPeriod}</span></div>
                            <input type="range" min="7" max="30" step="1" value={atrPeriod} onChange={(e) => onChange({ atrPeriod: Number(e.target.value) })} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-gray-400 cursor-pointer" />
                        </div>
                    </div>

                    {/* 기본값 초기화 */}
                    <button
                        type="button"
                        onClick={() => onSyncDefaults(strategyName)}
                        className="text-[10px] sm:text-xs text-gray-500 hover:text-primary transition-colors underline underline-offset-2"
                    >
                        전략 기본값으로 초기화
                    </button>
                </div>
            )}
        </div>
    );
}
