'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Key, BarChart3, Bot, Check, ChevronRight, X } from 'lucide-react';

const STORAGE_KEY = 'onboarding_dismissed';

interface OnboardingStep {
    id: string;
    icon: React.ReactNode;
    title: string;
    description: string;
    href: string;
    completed: boolean;
}

interface OnboardingGuideProps {
    hasKeys: boolean;
    hasBacktests: boolean;
    hasBots: boolean;
}

export default function OnboardingGuide({ hasKeys, hasBacktests, hasBots }: OnboardingGuideProps) {
    const router = useRouter();
    const [dismissed, setDismissed] = useState(true); // 기본 숨김, mount 후 확인

    useEffect(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        setDismissed(stored === 'true');
    }, []);

    const handleDismiss = useCallback(() => {
        localStorage.setItem(STORAGE_KEY, 'true');
        setDismissed(true);
    }, []);

    if (dismissed) return null;

    const steps: OnboardingStep[] = [
        {
            id: 'keys',
            icon: <Key className="w-5 h-5" />,
            title: 'API 키 등록',
            description: 'Upbit API 키를 등록하여 거래소를 연결하세요.',
            href: '/dashboard/keys',
            completed: hasKeys,
        },
        {
            id: 'backtest',
            icon: <BarChart3 className="w-5 h-5" />,
            title: '백테스트 실행',
            description: '전략을 먼저 검증하고 성과를 확인하세요.',
            href: '/dashboard/backtest',
            completed: hasBacktests,
        },
        {
            id: 'bot',
            icon: <Bot className="w-5 h-5" />,
            title: '봇 생성',
            description: '검증된 전략으로 모의투자를 시작하세요.',
            href: '/dashboard',
            completed: hasBots,
        },
    ];

    const completedCount = steps.filter((s) => s.completed).length;
    const allCompleted = completedCount === steps.length;
    const progressPercent = Math.round((completedCount / steps.length) * 100);

    return (
        <section
            className="mb-6 rounded-xl border border-th-border bg-th-card overflow-hidden"
            aria-label="시작 가이드"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-th-border-light">
                <div className="flex items-center gap-3">
                    <h2 className="text-sm font-bold text-th-text">
                        {allCompleted ? '🎉 설정 완료!' : '시작 가이드'}
                    </h2>
                    <span className="text-xs text-th-text-muted">
                        {completedCount}/{steps.length} 완료
                    </span>
                </div>
                <button
                    onClick={handleDismiss}
                    className="text-th-text-muted hover:text-th-text-secondary transition-colors text-xs flex items-center gap-1"
                    aria-label="가이드 닫기"
                >
                    <X className="w-3.5 h-3.5" />
                    다시 보지 않기
                </button>
            </div>

            {/* Progress bar */}
            <div className="h-0.5 bg-th-border-light">
                <div
                    className="h-full bg-primary transition-all duration-500 ease-out"
                    style={{ width: `${progressPercent}%` }}
                />
            </div>

            {/* Steps */}
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-th-border-light">
                {steps.map((step, index) => (
                    <button
                        key={step.id}
                        onClick={() => router.push(step.href)}
                        className="flex items-center gap-4 px-5 py-4 text-left hover:bg-th-hover transition-colors group"
                    >
                        {/* Step number / check */}
                        <div
                            className={[
                                'flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-colors',
                                step.completed
                                    ? 'bg-emerald-500/15 text-emerald-400'
                                    : 'bg-th-card text-th-text-muted group-hover:text-th-text-secondary',
                            ].join(' ')}
                        >
                            {step.completed ? (
                                <Check className="w-4.5 h-4.5" />
                            ) : (
                                step.icon
                            )}
                        </div>

                        {/* Text */}
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] sm:text-xs font-bold text-th-text-muted uppercase tracking-wider">
                                    Step {index + 1}
                                </span>
                                {step.completed && (
                                    <span className="text-[10px] sm:text-xs font-medium text-emerald-500">
                                        완료
                                    </span>
                                )}
                            </div>
                            <p className={[
                                'text-sm font-medium mt-0.5',
                                step.completed ? 'text-th-text-muted' : 'text-th-text',
                            ].join(' ')}>
                                {step.title}
                            </p>
                            <p className="text-xs text-th-text-muted mt-0.5 truncate">
                                {step.description}
                            </p>
                        </div>

                        {/* Arrow */}
                        {!step.completed && (
                            <ChevronRight className="w-4 h-4 text-th-text-muted group-hover:text-th-text-secondary transition-colors flex-shrink-0" />
                        )}
                    </button>
                ))}
            </div>
        </section>
    );
}
