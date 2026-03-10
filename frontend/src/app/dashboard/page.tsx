'use client';
import { useState, useEffect, useCallback } from 'react';
import { Play, StopCircle, Activity, Settings2, BarChart2, AlertTriangle, TrendingUp, TrendingDown, Clock, Wallet, ArrowUpRight, Zap, ListFilter } from 'lucide-react';
import api from '@/lib/api';
import StatCard from '@/components/ui/StatCard';
import RiskDisclaimerModal from '@/components/RiskDisclaimerModal';

export default function DashboardPage() {
    const [isBotActive, setIsBotActive] = useState(false);
    const [loading, setLoading] = useState(true);
    const [tradeLogs, setTradeLogs] = useState<any[]>([]);
    const [showRiskModal, setShowRiskModal] = useState(false);
    const [botId, setBotId] = useState<number | null>(null);

    const fetchStatusAndLogs = useCallback(async (id: number) => {
        try {
            const statusRes = await api.get(`/bot/status/${id}`);
            setIsBotActive(statusRes.data.bot_status === 'Running');

            const logRes = await api.get(`/bot/logs/${id}`);
            setTradeLogs(logRes.data);
        } catch (err) {
            console.error("상태 및 로그를 불러올 수 없습니다", err);
        }
    }, []);

    useEffect(() => {
        const initializeBotId = async () => {
            try {
                const res = await api.get('/bot/list');
                const bots: any[] = res.data;
                if (bots.length > 0) {
                    const firstId = bots[0].id;
                    setBotId(firstId);
                    await fetchStatusAndLogs(firstId);
                }
            } catch (err) {
                console.error("봇 목록을 불러올 수 없습니다", err);
            } finally {
                setLoading(false);
            }
        };

        initializeBotId();
    }, [fetchStatusAndLogs]);

    useEffect(() => {
        if (botId === null) return;
        const interval = setInterval(() => {
            fetchStatusAndLogs(botId);
        }, 10000);
        return () => clearInterval(interval);
    }, [botId, fetchStatusAndLogs]);

    const handleStartClick = () => {
        setShowRiskModal(true);
    };

    const handleRiskConfirm = async () => {
        setShowRiskModal(false);
        if (botId === null) return;
        try {
            await api.post(`/bot/start/${botId}`);
            setIsBotActive(true);
        } catch {
            alert("서버 연결에 실패했거나 권한이 없습니다.");
        }
    };

    const handleStop = async () => {
        if (botId === null) return;
        try {
            await api.post(`/bot/stop/${botId}`);
            setIsBotActive(false);
        } catch {
            alert("서버 연결에 실패했거나 권한이 없습니다.");
        }
    };

    if (loading) return (
        <div className="flex items-center justify-center h-[80vh]">
            <div className="flex flex-col items-center gap-4">
                <div className="w-10 h-10 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
                <p className="text-gray-500 text-sm font-medium">데이터 불러오는 중...</p>
            </div>
        </div>
    );

    return (
        <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in-up">
            {showRiskModal && (
                <RiskDisclaimerModal
                    onConfirm={handleRiskConfirm}
                    onCancel={() => setShowRiskModal(false)}
                />
            )}
            <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold mb-1 text-white">트레이딩 대시보드</h1>
                    <p className="text-sm text-gray-500">모멘텀 돌파 전략 V1.0 - 실시간 모니터링</p>
                </div>

                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs">
                    <div className="w-1.5 h-1.5 rounded-full bg-secondary"></div>
                    <span className="font-medium text-gray-300">UPBIT 연결됨</span>
                </div>
            </header>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden group">
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">엔진 상태</h3>
                            {isBotActive ? <Zap className="w-4 h-4 text-secondary" /> : <Activity className="w-4 h-4 text-gray-600" />}
                        </div>
                        <div className="flex items-center gap-2.5">
                            <div className={`w-2.5 h-2.5 rounded-full ${isBotActive ? 'bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-gray-600'}`}></div>
                            <span className="text-xl font-bold text-white">{isBotActive ? 'ACTIVE' : 'OFFLINE'}</span>
                        </div>
                    </div>
                </div>

                <StatCard
                    title="운용 자산"
                    value="₩1,000,000"
                    icon={<Wallet className="w-4 h-4" />}
                    accentColor="from-primary/10"
                    subtitle={<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/10 text-[10px] text-primary font-semibold">Paper Trading</span>}
                />

                <StatCard
                    title="일일 수익률"
                    value="--"
                    icon={<TrendingUp className="w-4 h-4" />}
                    accentColor="from-secondary/10"
                    subtitle={<span className="text-gray-500 text-xs font-semibold">N/A</span>}
                />

                <StatCard
                    title="승률"
                    value="--"
                    icon={<ArrowUpRight className="w-4 h-4" />}
                    accentColor="from-accent/10"
                    subtitle={<span className="text-[11px] text-gray-500">최근 50회 거래 기준</span>}
                />
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                {/* Control Panel */}
                <div className="lg:col-span-4 space-y-6">
                    <div className="glass-panel p-6 rounded-2xl">
                        <h3 className="text-base font-bold mb-6 flex items-center gap-2.5">
                            <Settings2 className="w-5 h-5 text-primary" />
                            시스템 제어
                        </h3>

                        {isBotActive ? (
                            <button
                                onClick={handleStop}
                                disabled={botId === null}
                                className="w-full flex items-center justify-center gap-2.5 py-3.5 bg-red-500/[0.08] hover:bg-red-500/[0.15] text-red-400 border border-red-500/20 rounded-xl font-semibold text-sm mb-6 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                <StopCircle className="w-5 h-5" />
                                엔진 정지
                            </button>
                        ) : (
                            <button
                                onClick={handleStartClick}
                                disabled={botId === null}
                                className="w-full flex items-center justify-center gap-2.5 py-3.5 bg-primary hover:bg-primary-dark text-white rounded-xl font-semibold text-sm shadow-glow-primary mb-6 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                <Play className="w-5 h-5" />
                                엔진 가동
                            </button>
                        )}

                        <div className="space-y-3">
                            <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04] flex items-center justify-between">
                                <div>
                                    <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">Symbol</p>
                                    <p className="text-sm font-semibold text-white">BTC/KRW</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">Timeframe</p>
                                    <p className="text-sm font-semibold text-white">1H</p>
                                </div>
                            </div>

                            <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                                <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">Strategy</p>
                                <p className="text-sm font-semibold text-primary">Momentum Breakout V1.2</p>
                            </div>
                        </div>

                        {!isBotActive && (
                            <div className="mt-5 flex items-start gap-3 p-4 bg-amber-500/[0.04] rounded-xl border border-amber-500/10">
                                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                                <p className="text-xs text-amber-500/80 leading-relaxed">
                                    엔진이 정지된 상태입니다. 자동 매매가 비활성화되었습니다.
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Timeline */}
                <div className="lg:col-span-8">
                    <div className="glass-panel p-6 rounded-2xl min-h-[500px] flex flex-col">
                        <div className="flex justify-between items-center mb-6 pb-4 border-b border-white/[0.04]">
                            <h3 className="text-base font-bold flex items-center gap-2.5">
                                <BarChart2 className="w-5 h-5 text-secondary" />
                                실행 타임라인
                            </h3>
                            <button aria-label="타임라인 필터" className="flex items-center gap-1.5 text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] px-3 py-2 rounded-lg border border-white/[0.06] transition-colors text-gray-400">
                                <ListFilter className="w-3.5 h-3.5" />
                                필터
                            </button>
                        </div>

                        <div className="space-y-3 flex-1 overflow-y-auto">
                            {tradeLogs.length > 0 ? tradeLogs.map((log) => (
                                <div key={log.id} className={`group p-5 rounded-xl border transition-colors ${log.side === 'BUY' ? 'bg-primary/[0.03] border-primary/10 hover:border-primary/20' : 'bg-red-500/[0.03] border-red-500/10 hover:border-red-500/20'}`}>
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${log.side === 'BUY' ? 'bg-primary/10 text-primary' : 'bg-red-500/10 text-red-400'}`}>
                                                {log.side === 'BUY' ? <ArrowUpRight className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                            </div>
                                            <div>
                                                <p className={`text-sm font-bold ${log.side === 'BUY' ? 'text-primary' : 'text-red-400'}`}>
                                                    {log.side === 'BUY' ? '매수' : '매도'}
                                                </p>
                                                <p className="text-[10px] text-gray-500 font-medium">{log.symbol} · {log.timestamp}</p>
                                            </div>
                                        </div>
                                        {log.pnl != null && (
                                            <div className="text-right">
                                                <p className={`text-base font-bold ${log.pnl > 0 ? 'text-secondary' : 'text-red-400'}`}>
                                                    {log.pnl > 0 ? '+' : ''}₩{Number(log.pnl).toLocaleString()}
                                                </p>
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-6 pt-3 border-t border-white/[0.04]">
                                        <div>
                                            <p className="text-[10px] text-gray-500 mb-0.5">체결가</p>
                                            <p className="font-mono text-sm text-white font-medium">₩{Number(log.price ?? 0).toLocaleString()}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-gray-500 mb-0.5">수량</p>
                                            <p className="font-mono text-sm text-white font-medium">{log.amount}</p>
                                        </div>
                                        <div className="ml-auto text-right">
                                            <p className="text-[10px] text-gray-500 mb-0.5">트리거</p>
                                            <p className="text-xs text-secondary font-medium">{log.reason}</p>
                                        </div>
                                    </div>
                                </div>
                            )) : (
                                <div className="flex flex-col items-center justify-center py-16 text-center">
                                    <Clock className="w-12 h-12 mb-4 text-gray-700" />
                                    <p className="text-base font-semibold text-gray-400">거래 내역이 없습니다</p>
                                    <p className="text-sm text-gray-600 mt-1">엔진을 가동하면 거래 타임라인이 표시됩니다.</p>
                                </div>
                            )}

                            {isBotActive && (
                                <div className="flex items-center gap-3 p-4 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                                    <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                                        <Activity className="w-4 h-4 text-primary animate-pulse" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-white font-medium">실시간 스트리밍 중...</p>
                                        <p className="text-[10px] text-gray-500">다음 돌파 패턴을 탐색하고 있습니다</p>
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
