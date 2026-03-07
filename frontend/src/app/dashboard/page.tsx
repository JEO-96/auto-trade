'use client';
import { useState, useEffect } from 'react';
import { Play, StopCircle, Activity, ActivitySquare, Settings2, BarChart2, CheckCircle2, AlertTriangle, TrendingUp, TrendingDown, Clock, ShieldCheck, Wallet } from 'lucide-react';
import api from '@/lib/api';
import StatCard from '@/components/ui/StatCard';

export default function DashboardPage() {
    const [isBotActive, setIsBotActive] = useState(false);
    const [loading, setLoading] = useState(true);
    const [tradeLogs, setTradeLogs] = useState<any[]>([]);

    const botId = 1; // 임시 봇 ID (추후 로그인 유저 연동)

    // 현재 봇 상태 및 로그 가져오기
    const fetchStatusAndLogs = async () => {
        try {
            const statusRes = await api.get(`/bot/status/${botId}`);
            setIsBotActive(statusRes.data.bot_status === 'Running');

            const logRes = await api.get(`/bot/logs/${botId}`);
            setTradeLogs(logRes.data);
        } catch (error) {
            console.error("상태 및 로그를 불러올 수 없습니다", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatusAndLogs();

        // Polling every 10 seconds for live updates
        const interval = setInterval(() => {
            fetchStatusAndLogs();
        }, 10000);

        return () => clearInterval(interval);
    }, []);

    const toggleEngine = async () => {
        try {
            if (isBotActive) {
                await api.post(`/bot/stop/${botId}`);
                setIsBotActive(false);
            } else {
                await api.post(`/bot/start/${botId}`);
                setIsBotActive(true);
            }
        } catch (error: any) {
            alert("서버 연결에 실패했거나 권한이 없습니다. (로그인 필요)");
        }
    };

    if (loading) return <div className="p-8 text-center">로딩중...</div>;

    return (
        <div className="p-8 max-w-6xl mx-auto animate-fade-in-up">
            <header className="mb-8 flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold mb-2">트레이딩 대시보드</h1>
                    <p className="text-gray-400">제임스의 모멘텀 돌파 봇을 실시간으로 관리하고 모니터링하세요.</p>
                </div>
            </header>

            {/* Main Stats/Status Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {/* Status Card */}
                <div className="glass-panel p-6 rounded-2xl border-t-4 border-t-primary relative overflow-hidden flex flex-col justify-between">
                    <div>
                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">봇 구동 상태</h3>
                        <div className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${isBotActive ? 'bg-secondary animate-pulse shadow-[0_0_10px_#10B981]' : 'bg-gray-600'}`}></div>
                            <span className="text-2xl font-bold">{isBotActive ? '실시간 가동 중' : '시스템 정지됨'}</span>
                        </div>
                    </div>
                    <div className="mt-4 text-sm text-gray-400">
                        BTC/KRW 1시간봉 모니터링 중
                    </div>
                </div>

                <StatCard
                    title="운용 자산"
                    value={<>₩1,000,000 <span className="text-sm font-normal text-secondary ml-2 border border-secondary/30 bg-secondary/10 px-2 py-1 rounded-md">모의투자</span></>}
                    accentColor="bg-secondary/10"
                />

                <StatCard
                    title="누적 수익"
                    value="₩0"
                    accentColor="bg-accent/10"
                    subtitle="현재 완료된 주문 없음"
                />
            </div>

            {/* Control Panel */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Active Controls */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="glass-panel p-6 rounded-2xl">
                        <h3 className="text-xl font-bold mb-6 flex items-center gap-2"><Settings2 className="w-5 h-5 text-primary" /> 시스템 제어</h3>

                        {isBotActive ? (
                            <button
                                onClick={toggleEngine}
                                className="w-full flex items-center justify-center gap-2 py-4 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 rounded-xl font-bold mb-4 transition-colors"
                            >
                                <StopCircle className="w-6 h-6" /> 봇 엔진 정지하기
                            </button>
                        ) : (
                            <button
                                onClick={toggleEngine}
                                className="w-full flex items-center justify-center gap-2 py-4 bg-primary hover:bg-blue-600 text-white rounded-xl font-bold shadow-[0_0_15px_rgba(59,130,246,0.3)] mb-4 transition-all"
                            >
                                <Play className="w-6 h-6" /> 봇 엔진 실행하기
                            </button>
                        )}

                        <div className="bg-surface/50 p-4 rounded-lg border border-gray-700/50">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-gray-400 text-sm">감시 페어</span>
                                <span className="font-semibold">BTC/KRW</span>
                            </div>
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-gray-400 text-sm">봉 분석 주기</span>
                                <span className="font-semibold">1 시간봉</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">활성 전략</span>
                                <span className="text-primary font-medium tracking-wide">제임스 돌파전략 v1.0</span>
                            </div>
                        </div>

                        {!isBotActive && (
                            <div className="mt-4 flex items-start gap-2 text-yellow-500/80 bg-yellow-500/10 p-3 rounded-lg border border-yellow-500/20 text-xs">
                                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                <p>현재 봇 엔진이 꺼져있습니다. 시장 모니터링 및 자동매매가 진행되지 않습니다.</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Position Log / Activity */}
                <div className="lg:col-span-2">
                    <div className="glass-panel p-6 rounded-2xl h-full min-h-[400px]">
                        <div className="flex justify-between items-center mb-6 border-b border-gray-800 pb-4">
                            <h3 className="text-xl font-bold flex items-center gap-2"><BarChart2 className="w-5 h-5 text-secondary" /> 실시간 로그</h3>
                            <button className="text-sm bg-surface hover:bg-gray-800 px-3 py-1 rounded-md border border-gray-700 transition-colors">로그 초기화</button>
                        </div>

                        <div className="space-y-4">
                            {tradeLogs.map((log) => (
                                <div key={log.id} className={`flex items-start gap-4 p-3 rounded-lg border ${log.side === 'BUY' ? 'bg-primary/10 border-primary/20' : 'bg-red-500/10 border-red-500/20'}`}>
                                    <div className={`mt-0.5 w-6 h-6 flex items-center justify-center rounded-full ${log.side === 'BUY' ? 'bg-primary/20 text-primary' : 'bg-red-500/20 text-red-500'}`}>
                                        <BarChart2 className="w-3 h-3" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex justify-between">
                                            <p className={`text-sm font-bold ${log.side === 'BUY' ? 'text-primary' : 'text-red-500'}`}>
                                                {log.side === 'BUY' ? '매수 진입' : '매도 청산'} - {log.symbol}
                                            </p>
                                            <span className="text-xs text-gray-500">{log.timestamp}</span>
                                        </div>
                                        <div className="flex justify-between items-center mt-2">
                                            <p className="text-xs text-gray-300">
                                                가격: <span className="font-mono text-white">₩{log.price.toLocaleString()}</span> |
                                                수량: <span className="font-mono text-white">{log.amount}</span>
                                            </p>
                                            {log.pnl !== null && (
                                                <p className={`text-xs font-bold ${log.pnl > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                    {log.pnl > 0 ? '+' : ''}{log.pnl > 0 ? '₩' : '-₩'}{Math.abs(log.pnl).toLocaleString()}
                                                </p>
                                            )}
                                        </div>
                                        <p className="text-xs text-gray-400 mt-1 italic font-medium">실행사유: {log.reason}</p>
                                    </div>
                                </div>
                            ))}

                            {isBotActive && (
                                <div className="flex items-start gap-4 p-3 bg-surface/30 rounded-lg border border-gray-800/50">
                                    <Play className="w-5 h-5 text-primary mt-0.5 animate-pulse" />
                                    <div>
                                        <p className="text-sm text-gray-300 font-medium">실시간 시장 감시 중...</p>
                                        <p className="text-xs text-gray-500 mt-1">새로운 진입 조건을 탐색하고 있습니다.</p>
                                    </div>
                                </div>
                            )}

                            {!isBotActive && tradeLogs.length === 0 && (
                                <div className="flex items-start gap-4 p-3 bg-surface/30 rounded-lg border border-gray-800/50">
                                    <Clock className="w-5 h-5 text-gray-500 mt-0.5" />
                                    <div>
                                        <p className="text-sm font-medium">시스템 대기 상태</p>
                                        <p className="text-xs text-gray-400 mt-1">시장 조건 추적을 시작할 준비가 되었습니다.</p>
                                    </div>
                                </div>
                            )}
                        </div>

                    </div>
                </div>

            </div>
        </div>
    );
}
