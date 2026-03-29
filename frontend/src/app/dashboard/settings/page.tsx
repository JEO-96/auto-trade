'use client';

import React, { useState, useEffect } from 'react';
import { Settings, ShieldAlert, Eye, EyeOff } from 'lucide-react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import PageContainer from '@/components/ui/PageContainer';
import { useAuth } from '@/contexts/AuthContext';
import { updateStrategyVisibility } from '@/lib/api/settings';
import { useStrategies } from '@/lib/useStrategies';
import { getErrorMessage } from '@/lib/utils';

export default function SettingsPage() {
    const { user, isLoading: authLoading } = useAuth();
    const { botStrategies, loading: strategiesLoading } = useStrategies();
    const [savingVisibility, setSavingVisibility] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 전략 공개 여부
    const [visibility, setVisibility] = useState<Record<string, boolean>>({});

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
                    <ShieldAlert className="w-16 h-16 text-th-text-muted mb-4" />
                    <h2 className="text-xl font-bold text-th-text mb-2">접근 권한이 없습니다</h2>
                    <p className="text-sm text-th-text-muted">이 페이지는 관리자만 접근할 수 있습니다.</p>
                </div>
            </PageContainer>
        );
    }

    if (strategiesLoading) {
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
                <h1 className="text-2xl font-bold mb-1 text-th-text flex items-center gap-2">
                    <Settings className="w-6 h-6 text-primary" />
                    시스템 설정
                </h1>
                <p className="text-sm text-th-text-muted">
                    전략 공개 여부를 관리합니다.
                </p>
            </header>

            {error && (
                <div className="glass-panel p-4 rounded-xl border-red-500/20 bg-red-500/[0.04] text-red-400 text-sm font-medium mb-6">
                    {error}
                </div>
            )}

            {/* 전략 공개 설정 */}
            <section className="mb-8">
                <h2 className="text-lg font-bold text-th-text mb-3 flex items-center gap-2">
                    <Eye className="w-5 h-5 text-primary" />
                    전략 공개 설정
                </h2>
                <p className="text-xs text-th-text-muted mb-4">
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
                                        <p className="text-sm font-bold text-th-text">{s.label}</p>
                                        <p className="text-[10px] sm:text-xs text-th-text-muted font-mono">{s.value}</p>
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

        </PageContainer>
    );
}
