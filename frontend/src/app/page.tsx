'use client';
import React from 'react';
import { ShieldCheck, Zap, ArrowRight, TrendingUp, LayoutDashboard } from 'lucide-react';
import Logo from '@/components/Logo';
import Link from 'next/link';
import CountUp from '@/components/ui/CountUp';

export default function Home() {
    return (
        <main className="flex min-h-screen flex-col relative overflow-hidden bg-background">
            {/* Navigation */}
            <header className="fixed top-0 w-full z-50 bg-background/60 backdrop-blur-xl border-b border-th-border-light py-4 px-6 md:px-12">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <Logo size="md" />

                    <Link
                        href="/dashboard"
                        className="px-5 py-2 text-sm font-semibold bg-white/[0.06] hover:bg-white/[0.1] text-th-text rounded-lg transition-all border border-white/[0.06] flex items-center gap-2"
                    >
                        <LayoutDashboard className="w-4 h-4" />
                        대시보드
                    </Link>
                </div>
            </header>

            {/* Background Glows */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/[0.08] rounded-full blur-[150px] pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/[0.08] rounded-full blur-[150px] pointer-events-none" />

            <div className="z-10 max-w-5xl w-full mx-auto flex flex-col items-center pt-36 pb-20 px-6">
                {/* Hero */}
                <div className="text-center mb-24 animate-fade-in-up">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-primary-light text-xs font-medium mb-8">
                        <span className="relative flex h-1.5 w-1.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary"></span>
                        </span>
                        전략 검증 플랫폼
                    </div>

                    <h1 className="text-[2rem] md:text-6xl font-extrabold tracking-tight mb-6 leading-[1.1]">
                        <span className="text-th-text">백테스트로 검증된 전략,</span><br />
                        <span className="text-gradient-primary">수익으로 증명합니다</span>
                    </h1>

                    <p className="text-base md:text-lg text-th-text-secondary max-w-xl mx-auto mb-10 leading-relaxed [text-wrap:pretty]">
                        직접 백테스트하고, 신뢰할 수 있는 전략으로 모의투자하세요.<br className="hidden sm:block" />
                        베타 기간 중 무료로 모든 기능을 이용하세요.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-3 justify-center">
                        <Link href="/login" className="group px-8 py-3.5 bg-primary hover:bg-primary-dark transition-all font-semibold rounded-xl shadow-glow-primary flex items-center justify-center gap-2 text-sm">
                            카카오로 시작하기
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </Link>
                        <Link href="/login?redirect=/dashboard/backtest" className="px-8 py-3.5 rounded-xl border border-th-border hover:bg-white/[0.04] transition-all flex items-center justify-center gap-2 text-sm font-semibold text-th-text-secondary">
                            백테스트 먼저 해보기
                        </Link>
                    </div>
                </div>

                {/* Hero Stats Counter */}
                <div className="grid grid-cols-3 gap-6 w-full max-w-lg mx-auto mb-24">
                    {[
                        { end: 21, suffix: '개', label: '검증된 전략' },
                        { end: 4, suffix: '개', label: '타임프레임' },
                        { end: 24, suffix: 'h', label: '자동 모니터링' },
                    ].map((stat) => (
                        <div key={stat.label} className="text-center">
                            <p className="text-3xl md:text-4xl font-extrabold text-th-text tracking-tight">
                                <CountUp end={stat.end} suffix={stat.suffix} />
                            </p>
                            <p className="text-xs text-th-text-muted mt-1 font-medium">{stat.label}</p>
                        </div>
                    ))}
                </div>

                {/* How it works */}
                <div className="w-full mb-24">
                    <h2 className="text-sm font-bold text-th-text-muted uppercase tracking-wider mb-6 text-center">이렇게 사용하세요</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                        {[
                            {
                                step: '1',
                                icon: <Zap className="w-5 h-5" />,
                                bgClass: 'bg-primary/10 border-primary/10',
                                textClass: 'text-primary',
                                title: '전략 백테스트',
                                desc: '21개 전략 중 선택하고 과거 데이터로 수익률, 승률, 최대 낙폭을 확인하세요.'
                            },
                            {
                                step: '2',
                                icon: <TrendingUp className="w-5 h-5" />,
                                bgClass: 'bg-secondary/10 border-secondary/10',
                                textClass: 'text-secondary',
                                title: '모의투자 봇 실행',
                                desc: '검증된 전략으로 모의투자 봇을 만들고 24시간 자동 매매를 시뮬레이션하세요.'
                            },
                            {
                                step: '3',
                                icon: <ShieldCheck className="w-5 h-5" />,
                                bgClass: 'bg-accent/10 border-accent/10',
                                textClass: 'text-accent',
                                title: '성과 분석 & 공유',
                                desc: '실시간 성과를 추적하고 커뮤니티에서 다른 트레이더와 전략을 비교하세요.'
                            }
                        ].map((feature) => (
                            <div key={feature.title} className="glass-panel glass-panel-hover p-8 rounded-2xl flex flex-col items-start">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className={`${feature.bgClass} p-3 rounded-xl border`}>
                                        <span className={feature.textClass}>{feature.icon}</span>
                                    </div>
                                    <span className="text-xs font-bold text-th-text-muted">{feature.step}단계</span>
                                </div>
                                <h3 className="text-lg font-bold mb-3 text-th-text">{feature.title}</h3>
                                <p className="text-sm text-th-text-secondary leading-relaxed [text-wrap:pretty]">{feature.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <footer className="w-full border-t border-th-border-light pt-8 pb-4">
                    <div className="flex flex-col items-center gap-6 text-xs text-th-text-muted">
                        {/* 투자 위험 고지 */}
                        <div className="text-center leading-relaxed max-w-lg [text-wrap:pretty]">
                            <p className="text-amber-500/80 font-medium mb-1">⚠ 투자 위험 고지</p>
                            <p>
                                본 서비스는 투자 자문이 아니며, 가상자산 투자는 원금 손실 위험이 있습니다.
                                과거 수익률은 미래를 보장하지 않습니다. 모든 투자 결정에 대한 책임은 이용자 본인에게 있습니다.
                            </p>
                        </div>

                        {/* 링크 */}
                        <div className="flex items-center gap-4">
                            <Link href="/terms" className="text-th-text-muted hover:text-th-text-secondary transition-colors underline underline-offset-2">
                                이용약관
                            </Link>
                            <span className="text-th-text-muted">|</span>
                            <Link href="/privacy" className="text-th-text-muted hover:text-th-text-secondary transition-colors underline underline-offset-2">
                                개인정보처리방침
                            </Link>
                        </div>

                        <p className="text-th-text-muted">© {new Date().getFullYear()} Backtested. All rights reserved.</p>
                    </div>
                </footer>
            </div>
        </main>
    )
}
