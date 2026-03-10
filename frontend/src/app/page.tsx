'use client';
import React from 'react';
import { Activity, ShieldCheck, Zap, ArrowRight, TrendingUp, BarChart3, LogIn, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
    return (
        <main className="flex min-h-screen flex-col relative overflow-hidden bg-background">
            {/* Navigation Header */}
            <header className="fixed top-0 w-full z-50 bg-black/40 backdrop-blur-xl border-b border-white/5 py-4 px-6 md:px-12 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary/20 rounded-lg flex items-center justify-center border border-primary/30 shadow-glow-primary">
                        <Activity className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                        <span className="text-lg font-extrabold tracking-tight text-white block leading-none">MOMENTUM</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <Link
                        href="/login"
                        className="hidden sm:flex items-center gap-2 px-4 py-2 text-sm font-semibold text-gray-300 hover:text-white transition-colors"
                    >
                        <LogIn className="w-4 h-4" />
                        기존 계정 로그인
                    </Link>
                    <Link
                        href="/dashboard"
                        className="px-6 py-2.5 text-sm font-bold bg-primary hover:bg-primary-dark text-white rounded-full transition-all shadow-glow-primary flex items-center gap-2"
                    >
                        <LayoutDashboard className="w-4 h-4" />
                        내 대시보드
                    </Link>
                </div>
            </header>

            {/* Ambient Background Glows */}
            <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-primary/20 rounded-full blur-[150px] animate-glow-pulse pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-accent/20 rounded-full blur-[150px] animate-glow-pulse pointer-events-none" />
            <div className="absolute top-[40%] left-[30%] w-[30%] h-[30%] bg-secondary/10 rounded-full blur-[120px] pointer-events-none" />

            <div className="z-10 max-w-6xl w-full mx-auto flex flex-col items-center pt-32 px-6">
                {/* Hero Section */}
                <div className="text-center mb-20 animate-fade-in-up">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-primary-light text-sm font-medium mb-8 backdrop-blur-md">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                        </span>
                        Next-Gen Algorithmic Trading
                    </div>

                    <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 leading-tight">
                        <span className="text-white">모멘텀 돌파</span><br />
                        <span className="text-gradient-primary">수익의 극대화를 경험하세요</span>
                    </h1>

                    <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed">
                        제임스의 검증된 모멘텀 돌파 전략으로 암호화폐 매매를 완벽하게 자동화하세요.
                        강력한 파이썬 엔진과 프리미엄 실시간 대시보드가 당신의 자산을 지킵니다.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-5 justify-center">
                        <Link href="/login" className="group px-10 py-5 bg-primary hover:bg-primary-dark transition-all font-black rounded-full shadow-glow-primary flex items-center justify-center gap-3 text-lg">
                            지금 시작하기 (카카오 로그인)
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </Link>
                        <Link href="/dashboard" className="px-10 py-5 rounded-full border border-white/10 hover:bg-white/5 transition-all flex items-center justify-center gap-3 text-lg font-bold">
                            대시보드로 바로가기
                        </Link>
                    </div>
                </div>

                {/* Features Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full">
                    <div className="glass-panel glass-panel-hover p-10 rounded-[2.5rem] flex flex-col items-start border-white/5">
                        <div className="bg-primary/20 p-4 rounded-2xl mb-8 group">
                            <Zap className="text-primary w-10 h-10 group-hover:scale-110 transition-transform" />
                        </div>
                        <h3 className="text-2xl font-bold mb-4 text-white">실시간 신호 포착</h3>
                        <p className="text-gray-400 leading-relaxed font-medium">
                            RSI 상향 돌파, MACD 교차, 거래량 폭증을 밀리초 단위로 추적하여 승률 높은 진입 시점을 찾아냅니다.
                        </p>
                    </div>

                    <div className="glass-panel glass-panel-hover p-10 rounded-[2.5rem] flex flex-col items-start border-white/5">
                        <div className="bg-secondary/20 p-4 rounded-2xl mb-8 group">
                            <TrendingUp className="text-secondary w-10 h-10 group-hover:scale-110 transition-transform" />
                        </div>
                        <h3 className="text-2xl font-bold mb-4 text-white">24/7 무중단 가동</h3>
                        <p className="text-gray-400 leading-relaxed font-medium">
                            CCXT API를 통한 전 세계 주요 거래소와의 완벽 연동으로 365일 지치지 않는 자동 매매를 실현합니다.
                        </p>
                    </div>

                    <div className="glass-panel glass-panel-hover p-10 rounded-[2.5rem] flex flex-col items-start border-white/5">
                        <div className="bg-accent/20 p-4 rounded-2xl mb-8 group">
                            <ShieldCheck className="text-accent w-10 h-10 group-hover:scale-110 transition-transform" />
                        </div>
                        <h3 className="text-2xl font-bold mb-4 text-white">스마트 리스크 관리</h3>
                        <p className="text-gray-400 leading-relaxed font-medium">
                            진입 캔들 저점 손절 및 다이나믹 익절 전략을 통해 하락장에서도 당신의 소중한 자산을 안전하게 보호합니다.
                        </p>
                    </div>
                </div>

                {/* Visual Accent */}
                <div className="mt-32 w-full glass-panel overflow-hidden rounded-[3rem] border-white/5 opacity-40 relative h-64 flex items-center justify-center p-8 mb-20">
                    <div className="absolute inset-0 bg-dot-pattern opacity-20" />
                    <BarChart3 className="w-32 h-32 text-white/5 animate-float" />
                    <p className="text-white/20 font-bold text-4xl uppercase tracking-[1em] select-none text-center hidden md:block">Autonomous Trading System</p>
                </div>
            </div>
        </main>
    )
}
