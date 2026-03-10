'use client';
import { useState, useEffect } from 'react';
import { Play, StopCircle, Activity, Settings2, BarChart2, AlertTriangle, TrendingUp, TrendingDown, Clock, Wallet, ArrowUpRight, Zap, ListFilter } from 'lucide-react';
import api from '@/lib/api';
import StatCard from '@/components/ui/StatCard';

export default function DashboardPage() {
    const [isBotActive, setIsBotActive] = useState(false);
    const [loading, setLoading] = useState(true);
    const [tradeLogs, setTradeLogs] = useState<any[]>([]);

    const botId = 1;

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

    if (loading) return (
        <div className="flex items-center justify-center h-[80vh]">
            <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                <p className="text-gray-400 font-bold animate-pulse">데이터 동기화 중...</p>
            </div>
        </div>
    );

    return (
        <div className="p-10 max-w-7xl mx-auto animate-fade-in-up">
            <header className="mb-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                    <h1 className="text-4xl font-extrabold mb-3 text-white tracking-tight">트레이딩 대시보드</h1>
                    <p className="text-gray-400 font-medium">제임스의 모멘텀 돌파 전략 V1.0 - 실시간 모니터링</p>
                </div>

                <div className="flex items-center gap-3 bg-white/5 p-2 rounded-2xl border border-white/10 backdrop-blur-md">
                    <div className="px-4 py-2 flex items-center gap-2">
                        <Wallet className="w-4 h-4 text-primary" />
                        <span className="text-sm font-bold">CONNECTED: UPBIT</span>
                    </div>
                </div>
            </header>

            {/* Main Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <div className="glass-panel glass-panel-hover p-8 rounded-[2rem] flex flex-col justify-between relative overflow-hidden group">
                    <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${isBotActive ? 'from-secondary/20' : 'from-gray-500/10'} blur-2xl opacity-50 group-hover:opacity-80 transition-opacity`} />
                    <div className="relative z-10 flex flex-col h-full">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-gray-400 text-xs font-bold uppercase tracking-[0.1em]">엔진 상태</h3>
                            {isBotActive ? <Zap className="w-5 h-5 text-secondary animate-pulse" /> : <Activity className="w-5 h-5 text-gray-500" />}
                        </div>
                        <div className="flex items-center gap-3 mt-auto">
                            <div className={`w-3.5 h-3.5 rounded-full ${isBotActive ? 'bg-secondary animate-glow-pulse shadow-glow-secondary' : 'bg-gray-600'}`}></div>
                            <span className="text-2xl font-extrabold text-white">{isBotActive ? 'ACTIVE' : 'OFFLINE'}</span>
                        </div>
                    </div>
                </div>

                <StatCard
                    title="운용 자산"
                    value="₩1,000,000"
                    icon={<Wallet className="w-5 h-5" />}
                    accentColor="from-primary/20"
                    subtitle={<span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/10 border border-primary/20 text-[10px] text-primary font-bold uppercase tracking-wider">Paper Trading</span>}
                />

                <StatCard
                    title="일일 수익률"
                    value="+4.20%"
                    icon={<TrendingUp className="w-5 h-5" />}
                    accentColor="from-secondary/20"
                    subtitle={<span className="text-secondary font-bold flex items-center gap-1 uppercase tracking-wider text-[10px]">+₩42,000 Today</span>}
                />

                <StatCard
                    title="승률 (WIN RATE)"
                    value="68.5%"
                    icon={<ArrowUpRight className="w-5 h-5" />}
                    accentColor="from-accent/20"
                    subtitle={<p className="text-[10px] uppercase tracking-wider font-bold text-gray-500">Based on last 50 trades</p>}
                />
            </div>

            {/* Dashboard Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Control Panel (Left/Top) */}
                <div className="lg:col-span-4 space-y-8">
                    <div className="glass-panel p-10 rounded-[2.5rem] border-white/5 relative overflow-hidden">
                        <h3 className="text-2xl font-extrabold mb-10 flex items-center gap-3">
                            <Settings2 className="w-6 h-6 text-primary" />
                            시스템 제어
                        </h3>

                        {isBotActive ? (
                            <button
                                onClick={toggleEngine}
                                className="w-full flex items-center justify-center gap-3 py-5 bg-danger/10 hover:bg-danger/20 text-danger border border-danger/30 rounded-2xl font-bold mb-8 transition-all duration-300 group"
                            >
                                <StopCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
                                엔진 강제 정지
                            </button>
                        ) : (
                            <button
                                onClick={toggleEngine}
                                className="w-full flex items-center justify-center gap-3 py-5 bg-primary hover:bg-primary-dark text-white rounded-2xl font-bold shadow-glow-primary mb-8 transition-all duration-300 group"
                            >
                                <Play className="w-6 h-6 group-hover:scale-110 transition-transform" />
                                엔진 가동 시작
                            </button>
                        )}

                        <div className="space-y-4">
                            <div className="p-5 bg-white/5 rounded-2xl border border-white/5 flex items-center justify-between">
                                <div>
                                    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1">Target Symbol</p>
                                    <p className="font-bold text-white">BTC/KRW</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1">Timeframe</p>
                                    <p className="font-bold text-white">1H Candle</p>
                                </div>
                            </div>

                            <div className="p-5 bg-white/5 rounded-2xl border border-white/5 flex items-center justify-between">
                                <div className="flex-1">
                                    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1">Active Strategy</p>
                                    <p className="font-bold text-primary truncate">Momentum Breakout V1.2</p>
                                </div>
                            </div>
                        </div>

                        {!isBotActive && (
                            <div className="mt-8 flex items-start gap-4 p-5 bg-yellow-500/5 rounded-2xl border border-yellow-500/10">
                                <AlertTriangle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
                                <p className="text-xs text-yellow-500/80 leading-relaxed font-medium">
                                    엔진이 정지된 상태입니다. 자동 매매 및 신호 알림이 비활성화되었습니다.
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Real-time Logs (Right/Bottom) */}
                <div className="lg:col-span-8">
                    <div className="glass-panel p-10 rounded-[2.5rem] min-h-[600px] flex flex-col">
                        <div className="flex justify-between items-center mb-10 border-b border-white/5 pb-8">
                            <h3 className="text-2xl font-extrabold flex items-center gap-3">
                                <BarChart2 className="w-6 h-6 text-secondary" />
                                실행 타임라인
                            </h3>
                            <button className="flex items-center gap-2 text-xs font-bold bg-white/5 hover:bg-white/10 px-4 py-2.5 rounded-xl border border-white/10 transition-all text-gray-300">
                                <ListFilter className="w-4 h-4" />
                                필터링
                            </button>
                        </div>

                        <div className="space-y-5 flex-1 overflow-y-auto custom-scrollbar">
                            {tradeLogs.length > 0 ? tradeLogs.map((log) => (
                                <div key={log.id} className={`group p-6 rounded-2xl border transition-all duration-300 hover:translate-x-2 ${log.side === 'BUY' ? 'bg-primary/5 border-primary/10 hover:border-primary/30' : 'bg-red-500/5 border-red-500/10 hover:border-red-500/30'}`}>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-4">
                                            <div className={`p-3 rounded-xl ${log.side === 'BUY' ? 'bg-primary/20 text-primary' : 'bg-red-500/20 text-red-500'}`}>
                                                {log.side === 'BUY' ? <ArrowUpRight className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                                            </div>
                                            <div>
                                                <p className={`text-lg font-extrabold ${log.side === 'BUY' ? 'text-primary' : 'text-red-500'}`}>
                                                    {log.side === 'BUY' ? 'POSITION OPEN' : 'POSITION CLOSED'}
                                                </p>
                                                <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">{log.symbol} • {log.timestamp}</p>
                                            </div>
                                        </div>
                                        {log.pnl !== null && (
                                            <div className="text-right">
                                                <p className={`text-xl font-black ${log.pnl > 0 ? 'text-secondary' : 'text-red-500'}`}>
                                                    {log.pnl > 0 ? '+' : ''}₩{log.pnl.toLocaleString()}
                                                </p>
                                                <p className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">Settled PnL</p>
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-8 py-4 px-2 border-t border-white/5 mt-4">
                                        <div>
                                            <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Execution Price</p>
                                            <p className="font-mono text-white font-bold">₩{log.price.toLocaleString()}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Quantity</p>
                                            <p className="font-mono text-white font-bold">{log.amount}</p>
                                        </div>
                                        <div className="ml-auto text-right">
                                            <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">Trigger</p>
                                            <p className="text-xs text-secondary font-bold">{log.reason}</p>
                                        </div>
                                    </div>
                                </div>
                            )) : (
                                <div className="flex flex-col items-center justify-center py-20 text-center opacity-40">
                                    <Clock className="w-16 h-16 mb-4 text-gray-500" />
                                    <p className="text-xl font-bold text-gray-300">엔진 가동 준비 완료</p>
                                    <p className="text-sm text-gray-400 mt-2">새로운 거래가 발생하면 이곳에 타임라인이 표시됩니다.</p>
                                </div>
                            )}

                            {isBotActive && (
                                <div className="flex items-center gap-4 p-6 bg-white/5 rounded-2xl border border-white/5 animate-pulse">
                                    <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center">
                                        <Activity className="w-5 h-5 text-primary" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-white font-bold">실시간 시장 데이터 스트리밍 중...</p>
                                        <p className="text-[10px] text-gray-500 font-medium uppercase tracking-[0.2em]">Searching for next breakout pattern</p>
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

