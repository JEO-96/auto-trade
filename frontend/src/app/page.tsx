'use client';
import React from 'react';
import { Activity, ShieldCheck, Zap, ArrowRight, TrendingUp, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
    return (
        <main className="flex min-h-screen flex-col relative overflow-hidden bg-background">
            {/* Navigation */}
            <header className="fixed top-0 w-full z-50 bg-background/60 backdrop-blur-xl border-b border-white/[0.04] py-4 px-6 md:px-12">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
                            <Activity className="w-4 h-4 text-primary" />
                        </div>
                        <span className="text-base font-extrabold tracking-tight text-white">BACKTESTED</span>
                    </div>

                    <Link
                        href="/dashboard"
                        className="px-5 py-2 text-sm font-semibold bg-white/[0.06] hover:bg-white/[0.1] text-white rounded-lg transition-all border border-white/[0.06] flex items-center gap-2"
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
                        Algorithmic Trading Platform
                    </div>

                    <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-6 leading-[1.1]">
                        <span className="text-white">백테스트로 검증된 전략,</span><br />
                        <span className="text-gradient-primary">수익으로 증명합니다</span>
                    </h1>

                    <p className="text-base md:text-lg text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed">
                        직접 백테스트하고, 신뢰할 수 있는 전략으로 자동매매하세요.<br className="hidden sm:block" />
                        수익이 날 때만 수수료를 내는 공정한 플랫폼입니다.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-3 justify-center">
                        <Link href="/login" className="group px-8 py-3.5 bg-primary hover:bg-primary-dark transition-all font-semibold rounded-xl shadow-glow-primary flex items-center justify-center gap-2 text-sm">
                            카카오로 시작하기
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </Link>
                        <Link href="/community" className="px-8 py-3.5 rounded-xl border border-white/[0.08] hover:bg-white/[0.04] transition-all flex items-center justify-center gap-2 text-sm font-semibold text-gray-300">
                            커뮤니티 둘러보기
                        </Link>
                    </div>
                </div>

                {/* Features */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full mb-24">
                    {[
                        {
                            icon: <Zap className="w-5 h-5" />,
                            bgClass: 'bg-primary/10 border-primary/10',
                            textClass: 'text-primary',
                            title: '백테스트로 검증',
                            desc: '실제 과거 데이터로 전략을 직접 검증하세요. 수익률, 승률, 최대 낙폭까지 투명하게 확인할 수 있습니다.'
                        },
                        {
                            icon: <TrendingUp className="w-5 h-5" />,
                            bgClass: 'bg-secondary/10 border-secondary/10',
                            textClass: 'text-secondary',
                            title: '성과 기반 수수료',
                            desc: '수익이 날 때만 10%의 수수료를 내고, 손실 시에는 10%를 돌려받습니다. 플랫폼과 사용자의 이해가 일치합니다.'
                        },
                        {
                            icon: <ShieldCheck className="w-5 h-5" />,
                            bgClass: 'bg-accent/10 border-accent/10',
                            textClass: 'text-accent',
                            title: '24시간 365일 자동매매',
                            desc: 'ATR 기반 동적 손절/익절과 다양한 전략으로 24시간 시장을 자동 모니터링하고 매매합니다.'
                        }
                    ].map((feature) => (
                        <div key={feature.title} className="glass-panel glass-panel-hover p-8 rounded-2xl flex flex-col items-start">
                            <div className={`${feature.bgClass} p-3 rounded-xl mb-6 border`}>
                                <span className={feature.textClass}>{feature.icon}</span>
                            </div>
                            <h3 className="text-lg font-bold mb-3 text-white">{feature.title}</h3>
                            <p className="text-sm text-gray-400 leading-relaxed">{feature.desc}</p>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <footer className="w-full border-t border-white/[0.04] pt-8 pb-4">
                    <div className="flex flex-col items-center gap-6 text-xs text-gray-500">
                        {/* 투자 위험 고지 */}
                        <div className="text-center leading-relaxed max-w-lg">
                            <p className="text-amber-500/80 font-medium mb-1">⚠ 투자 위험 고지</p>
                            <p>
                                본 서비스는 투자 자문이 아니며, 가상자산 투자는 원금 손실 위험이 있습니다.
                                과거 수익률은 미래를 보장하지 않습니다. 모든 투자 결정에 대한 책임은 이용자 본인에게 있습니다.
                            </p>
                        </div>

                        {/* 사업자 정보 */}
                        <div className="text-center leading-relaxed text-gray-600 space-y-1">
                            <p>
                                <span className="text-gray-500">플레이위드</span> | 대표 주은오 | 사업자등록번호 880-58-00862
                            </p>
                            <p>서울특별시 영등포구 경인로 882, 1103호(영등포동1가, 여의도씨티아이)</p>
                            <p>이메일 seal5945@gmail.com | 호스팅 Amazon Web Services</p>
                        </div>

                        {/* 링크 */}
                        <div className="flex items-center gap-4">
                            <Link href="/terms" className="text-gray-600 hover:text-gray-400 transition-colors underline underline-offset-2">
                                이용약관
                            </Link>
                            <span className="text-gray-700">|</span>
                            <Link href="/privacy" className="text-gray-600 hover:text-gray-400 transition-colors underline underline-offset-2">
                                개인정보처리방침
                            </Link>
                        </div>

                        <p className="text-gray-700">© 2025 Backtested. All rights reserved.</p>
                    </div>
                </footer>
            </div>
        </main>
    )
}
