'use client';
import React from 'react';
import { Activity, ShieldCheck, Zap, ArrowRight, TrendingUp, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
    return (
        <main className="flex min-h-screen min-h-[100dvh] flex-col relative overflow-hidden bg-background">
            {/* Navigation */}
            <header className="fixed top-0 w-full z-50 bg-background/60 backdrop-blur-xl border-b border-white/[0.04] py-3 px-4 sm:py-4 sm:px-6 md:px-12">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
                            <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary" />
                        </div>
                        <span className="text-sm sm:text-base font-extrabold tracking-tight text-white">MOMENTUM</span>
                    </div>

                    <Link
                        href="/dashboard"
                        className="px-3.5 py-1.5 sm:px-5 sm:py-2 text-xs sm:text-sm font-semibold bg-white/[0.06] hover:bg-white/[0.1] text-white rounded-lg transition-all border border-white/[0.06] flex items-center gap-1.5 sm:gap-2"
                    >
                        <LayoutDashboard className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                        대시보드
                    </Link>
                </div>
            </header>

            {/* Background Glows */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/[0.08] rounded-full blur-[150px] pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-accent/[0.08] rounded-full blur-[150px] pointer-events-none" />

            <div className="z-10 max-w-5xl w-full mx-auto flex flex-col items-center pt-24 sm:pt-36 pb-12 sm:pb-20 px-5 sm:px-6">
                {/* Hero */}
                <div className="text-center mb-14 sm:mb-24 animate-fade-in-up">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-primary-light text-[11px] sm:text-xs font-medium mb-6 sm:mb-8">
                        <span className="relative flex h-1.5 w-1.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary"></span>
                        </span>
                        Algorithmic Trading Platform
                    </div>

                    <h1 className="text-[28px] sm:text-4xl md:text-6xl font-extrabold tracking-tight mb-4 sm:mb-6 leading-[1.15] sm:leading-[1.1]">
                        <span className="text-white">모멘텀 돌파 전략으로</span><br />
                        <span className="text-gradient-primary">수익을 자동화하세요</span>
                    </h1>

                    <p className="text-sm sm:text-base md:text-lg text-gray-400 max-w-xl mx-auto mb-8 sm:mb-10 leading-relaxed px-2">
                        검증된 모멘텀 돌파 알고리즘과 실시간 대시보드로<br className="hidden sm:block" />
                        암호화폐 매매를 완벽하게 자동화합니다.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-3 justify-center px-4 sm:px-0">
                        <Link href="/login" className="group px-8 py-3.5 bg-primary hover:bg-primary-dark transition-all font-semibold rounded-xl shadow-glow-primary flex items-center justify-center gap-2 text-sm active:scale-[0.98]">
                            카카오로 시작하기
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </Link>
                        <Link href="/community" className="px-8 py-3.5 rounded-xl border border-white/[0.08] hover:bg-white/[0.04] transition-all flex items-center justify-center gap-2 text-sm font-semibold text-gray-300 active:scale-[0.98]">
                            커뮤니티 둘러보기
                        </Link>
                    </div>
                </div>

                {/* Features */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-5 w-full mb-14 sm:mb-24">
                    {[
                        {
                            icon: <Zap className="w-5 h-5" />,
                            bgClass: 'bg-primary/10 border-primary/10',
                            textClass: 'text-primary',
                            title: '실시간 신호 포착',
                            desc: 'RSI 상향 돌파, MACD 교차, 거래량 폭증을 밀리초 단위로 추적하여 최적의 진입 시점을 포착합니다.'
                        },
                        {
                            icon: <TrendingUp className="w-5 h-5" />,
                            bgClass: 'bg-secondary/10 border-secondary/10',
                            textClass: 'text-secondary',
                            title: '24/7 무중단 가동',
                            desc: 'CCXT API를 통한 주요 거래소와의 완벽 연동으로 365일 지치지 않는 자동 매매를 실현합니다.'
                        },
                        {
                            icon: <ShieldCheck className="w-5 h-5" />,
                            bgClass: 'bg-accent/10 border-accent/10',
                            textClass: 'text-accent',
                            title: '스마트 리스크 관리',
                            desc: '진입 캔들 저점 손절 및 다이나믹 익절 전략으로 하락장에서도 자산을 안전하게 보호합니다.'
                        }
                    ].map((feature) => (
                        <div key={feature.title} className="glass-panel glass-panel-hover p-6 sm:p-8 rounded-2xl flex flex-col items-start">
                            <div className={`${feature.bgClass} p-2.5 sm:p-3 rounded-xl mb-4 sm:mb-6 border`}>
                                <span className={feature.textClass}>{feature.icon}</span>
                            </div>
                            <h3 className="text-base sm:text-lg font-bold mb-2 sm:mb-3 text-white">{feature.title}</h3>
                            <p className="text-[13px] sm:text-sm text-gray-400 leading-relaxed">{feature.desc}</p>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <footer className="w-full border-t border-white/[0.04] pt-6 sm:pt-8 pb-4">
                    <div className="flex flex-col items-center gap-3 sm:gap-4 text-[11px] sm:text-xs text-gray-500">
                        <div className="flex items-center gap-2">
                            <Activity className="w-3.5 h-3.5 text-primary/50" />
                            <span className="font-medium">Momentum PRO</span>
                        </div>
                        <p className="text-center leading-relaxed max-w-lg px-2">
                            본 서비스는 투자 자문이 아니며, 가상자산 투자는 원금 손실 위험이 있습니다.
                            과거 수익률은 미래를 보장하지 않습니다. 모든 투자 결정에 대한 책임은 이용자 본인에게 있습니다.
                        </p>
                        <Link href="/terms" className="text-gray-600 hover:text-gray-400 transition-colors underline underline-offset-2">
                            서비스 이용약관
                        </Link>
                    </div>
                </footer>
            </div>
        </main>
    )
}
