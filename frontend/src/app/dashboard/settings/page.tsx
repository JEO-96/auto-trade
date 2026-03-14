'use client';

import React, { useState, useEffect } from 'react';
import { Settings, Save, CheckCircle2, ShieldAlert, ToggleLeft, ToggleRight, Eye, EyeOff } from 'lucide-react';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import PageContainer from '@/components/ui/PageContainer';
import { useAuth } from '@/contexts/AuthContext';
import { BACKTEST_TIMEFRAMES } from '@/lib/constants';
import { getBacktestSettings, updateBacktestSettings, updateStrategyVisibility } from '@/lib/api/settings';
import { useStrategies } from '@/lib/useStrategies';
import { getErrorMessage } from '@/lib/utils';

const ALL_TIMEFRAMES = BACKTEST_TIMEFRAMES;

export default function SettingsPage() {
    const { user, isLoading: authLoading } = useAuth();
    const { botStrategies, backtestStrategies, loading: strategiesLoading } = useStrategies();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [savingVisibility, setSavingVisibility] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 전략별 허용 타임프레임 매핑
    const [strategyTimeframes, setStrategyTimeframes] = useState<Record<string, string[]>>({});
    // 전략 공개 여부
    const [visibility, setVisibility] = useState<Record<string, boolean>>({});

    useEffect(() => {
        async function load() {
            try {
                const data = await getBacktestSettings();
                setStrategyTimeframes(data.strategy_timeframes);
            } catch (err) {
                console.error('설정 로드 실패', err);
                const fallback: Record<string, string[]> = {};
                for (const s of backtestStrategies) {
                    fallback[s.value] = ALL_TIMEFRAMES.map(t => t.value);
                }
                setStrategyTimeframes(fallback);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    // botStrategies 로드 시 visibility 초기화
    useEffect(() => {
        if (botStrategies.length > 0) {
            const vis: Record<string, boolean> = {};
            for (const s of botStrategies) {
                vis[s.value] = s.is_public !== false;
            }
            setVisibility(vis);
        }
    }, [botStrategies]);

    const isStrategyEnabled = (strategy: string) => {
        return strategy in strategyTimeframes && strategyTimeframes[strategy].length > 0;
    };

    const toggleStrategy = (strategy: string) => {
        setStrategyTimeframes(prev => {
            const next = { ...prev };
            if (isStrategyEnabled(strategy)) {
                // 전략 비활성화 (빈 배열이 아닌 삭제)
                delete next[strategy];
            } else {
                // 전략 활성화 — 모든 타임프레임 허용
                next[strategy] = ALL_TIMEFRAMES.map(t => t.value);
            }
            return next;
        });
    };

    const toggleTimeframe = (strategy: string, timeframe: string) => {
        setStrategyTimeframes(prev => {
            const current = prev[strategy] ?? [];
            const has = current.includes(timeframe);
            const updated = has
                ? current.filter(t => t !== timeframe)
                : [...current, timeframe];

            const next = { ...prev };
            if (updated.length === 0) {
                delete next[strategy];
            } else {
                next[strategy] = updated;
            }
            return next;
        });
    };

    const selectAllTimeframes = (strategy: string) => {
        setStrategyTimeframes(prev => ({
            ...prev,
            [strategy]: ALL_TIMEFRAMES.map(t => t.value),
        }));
    };

    const toggleVisibility = async (strategy: string) => {
        const newVal = !visibility[strategy];
        setVisibility(prev => ({ ...prev, [strategy]: newVal }));

        setSavingVisibility(true);
        setError(null);
        try {
            await updateStrategyVisibility({ [strategy]: newVal });
        } catch (err) {
            // 롤백
            setVisibility(prev => ({ ...prev, [strategy]: !newVal }));
            setError(getErrorMessage(err, '공개 설정 변경에 실패했습니다.'));
        } finally {
            setSavingVisibility(false);
        }
    };

    const handleSave = async () => {
        const enabledCount = Object.keys(strategyTimeframes).length;
        if (enabledCount === 0) {
            setError('최소 1개 이상의 전략을 활성화해야 합니다.');
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await updateBacktestSettings({ strategy_timeframes: strategyTimeframes });
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch (err) {
            setError(getErrorMessage(err, '설정 저장에 실패했습니다.'));
        } finally {
            setSaving(false);
        }
    };

    if (authLoading) {
        return (
            <PageContainer>
                <div className="flex items-center justify-center py-20">
                    <LoadingSpinner message="로딩 중..." />
                </div>
            </PageContainer>
        );
    }

    if (!user?.is_admin) {
        return (
            <PageContainer>
                <div className="flex flex-col items-center justify-center py-20 text-center">
                    <ShieldAlert className="w-16 h-16 text-gray-600 mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">접근 권한이 없습니다</h2>
                    <p className="text-sm text-gray-500">이 페이지는 관리자만 접근할 수 있습니다.</p>
                </div>
            </PageContainer>
        );
    }

    if (loading || strategiesLoading) {
        return (
            <PageContainer>
                <div className="flex items-center justify-center py-20">
                    <LoadingSpinner message="설정 불러오는 중..." />
                </div>
            </PageContainer>
        );
    }

    return (
        <PageContainer>
            <header className="mb-6">
                <h1 className="text-2xl font-bold mb-1 text-white flex items-center gap-2">
                    <Settings className="w-6 h-6 text-primary" />
                    시스템 설정
                </h1>
                <p className="text-sm text-gray-500">
                    전략 공개 여부와 백테스트 허용 타임프레임을 관리합니다.
                </p>
            </header>

            {error && (
                <div className="glass-panel p-4 rounded-xl border-red-500/20 bg-red-500/[0.04] text-red-400 text-sm font-medium mb-6">
                    {error}
                </div>
            )}

            {/* 전략 공개 설정 */}
            <section className="mb-8">
                <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                    <Eye className="w-5 h-5 text-primary" />
                    전략 공개 설정
                </h2>
                <p className="text-xs text-gray-500 mb-4">
                    비공개 전략은 관리자만 사용할 수 있습니다. 공개로 전환하면 모든 사용자에게 노출됩니다.
                </p>
                <div className="grid gap-3">
                    {botStrategies.map((s) => {
                        const isPublic = visibility[s.value] !== false;
                        return (
                            <div
                                key={s.value}
                                className={`glass-panel rounded-xl p-4 flex items-center justify-between transition-all ${
                                    isPublic ? 'border-primary/20' : 'border-yellow-500/20 bg-yellow-500/[0.02]'
                                }`}
                            >
                                <div className="flex items-center gap-3">
                                    {isPublic ? (
                                        <Eye className="w-4 h-4 text-primary" />
                                    ) : (
                                        <EyeOff className="w-4 h-4 text-yellow-500" />
                                    )}
                                    <div>
                                        <p className="text-sm font-bold text-white">{s.label}</p>
                                        <p className="text-[10px] text-gray-500 font-mono">{s.value}</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => toggleVisibility(s.value)}
                                    disabled={savingVisibility}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                        isPublic
                                            ? 'bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25'
                                            : 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/30 hover:bg-yellow-500/20'
                                    } disabled:opacity-50`}
                                >
                                    {isPublic ? '공개' : '비공개'}
                                </button>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* 백테스트 타임프레임 설정 */}
            <section>
                <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-primary" />
                    백테스트 타임프레임 설정
                </h2>
                <p className="text-xs text-gray-500 mb-4">
                    전략별 허용 타임프레임을 관리합니다.
                </p>
            </section>

            <div className="space-y-4">
                {backtestStrategies.map((s) => {
                    const enabled = isStrategyEnabled(s.value);
                    const selectedTimeframes = strategyTimeframes[s.value] ?? [];

                    return (
                        <div
                            key={s.value}
                            className={`glass-panel rounded-2xl p-5 transition-all ${
                                enabled ? 'border-primary/20' : 'opacity-50'
                            }`}
                        >
                            {/* 전략 헤더 */}
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={() => toggleStrategy(s.value)}
                                        className="text-primary hover:text-primary/80 transition-colors"
                                    >
                                        {enabled ? (
                                            <ToggleRight className="w-7 h-7" />
                                        ) : (
                                            <ToggleLeft className="w-7 h-7 text-gray-600" />
                                        )}
                                    </button>
                                    <div>
                                        <p className="text-sm font-bold text-white">{s.label}</p>
                                        <p className="text-[10px] text-gray-500 font-mono">{s.value}</p>
                                    </div>
                                </div>
                                {enabled && (
                                    <button
                                        onClick={() => selectAllTimeframes(s.value)}
                                        className="text-[10px] text-gray-500 hover:text-primary transition-colors px-2 py-1 rounded-lg border border-white/[0.06] hover:border-primary/20"
                                    >
                                        전체 선택
                                    </button>
                                )}
                            </div>

                            {/* 타임프레임 칩들 */}
                            {enabled && (
                                <div className="flex flex-wrap gap-2 pl-10">
                                    {ALL_TIMEFRAMES.map((t) => {
                                        const active = selectedTimeframes.includes(t.value);
                                        return (
                                            <button
                                                key={t.value}
                                                onClick={() => toggleTimeframe(s.value, t.value)}
                                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                                    active
                                                        ? 'bg-primary/15 text-primary border border-primary/30'
                                                        : 'bg-white/[0.02] text-gray-500 border border-white/[0.06] hover:border-white/[0.12]'
                                                }`}
                                            >
                                                {t.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* 저장 버튼 */}
            <div className="flex items-center gap-3 mt-6">
                <Button
                    onClick={handleSave}
                    loading={saving}
                    disabled={saved}
                    size="lg"
                >
                    {saved ? (
                        <>
                            <CheckCircle2 className="w-4 h-4" />
                            저장 완료
                        </>
                    ) : (
                        <>
                            <Save className="w-4 h-4" />
                            설정 저장
                        </>
                    )}
                </Button>
                {saved && (
                    <span className="text-sm text-secondary font-medium">설정이 저장되었습니다.</span>
                )}
            </div>
        </PageContainer>
    );
}
