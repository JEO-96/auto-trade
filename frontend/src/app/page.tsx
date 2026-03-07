import React from 'react';
import { Activity, ShieldCheck, Zap } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-8 relative overflow-hidden">
            {/* Background decorations */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/20 rounded-full blur-[120px] pointer-events-none" />

            <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">

                {/* Header Section */}
                <div className="text-center mb-16 animate-fade-in-up">
                    <h1 className="text-6xl font-extrabold tracking-tight mb-6">
                        <span className="text-gradient">모멘텀 돌파</span> 마스터
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                        제임스의 검증된 모멘텀 돌파 전략으로 암호화폐 매매를 완벽하게 자동화하세요.
                        강력한 파이썬 엔진과 프리미엄 대시보드의 만남.
                    </p>

                    <div className="mt-10 flex gap-4 justify-center">
                        <Link href="/login" className="px-8 py-4 bg-primary hover:bg-blue-600 transition-all font-semibold rounded-lg shadow-[0_0_20px_rgba(59,130,246,0.5)]">
                            지금 시작하기
                        </Link>
                        <Link href="/dashboard" className="px-8 py-4 bg-surface hover:bg-gray-800 border border-gray-700 transition-all font-semibold rounded-lg">
                            대시보드 보기
                        </Link>
                    </div>
                </div>

                {/* Features Section */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12">

                    <div className="glass-panel p-8 rounded-2xl transform hover:scale-105 transition-transform duration-300">
                        <div className="bg-primary/20 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                            <Zap className="text-primary w-8 h-8" />
                        </div>
                        <h3 className="text-2xl font-bold mb-3">실시간 신호 포착</h3>
                        <p className="text-gray-400">RSI 상향 돌파, MACD 교차, 거래량 폭증을 밀리초 단위로 추적합니다.</p>
                    </div>

                    <div className="glass-panel p-8 rounded-2xl transform hover:scale-105 transition-transform duration-300">
                        <div className="bg-secondary/20 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                            <Activity className="text-secondary w-8 h-8" />
                        </div>
                        <h3 className="text-2xl font-bold mb-3">24시간 자동 실행</h3>
                        <p className="text-gray-400">CCXT API 연동을 통해 감정 없는 기계적인 매수/매도를 책임집니다.</p>
                    </div>

                    <div className="glass-panel p-8 rounded-2xl transform hover:scale-105 transition-transform duration-300">
                        <div className="bg-accent/20 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                            <ShieldCheck className="text-accent w-8 h-8" />
                        </div>
                        <h3 className="text-2xl font-bold mb-3">철저한 리스크 관리</h3>
                        <p className="text-gray-400">진입 캔들 저점 손절 및 1:2 손익비를 칼같이 지켜 자금을 보호합니다.</p>
                    </div>

                </div>
            </div>
        </main>
    )
}
