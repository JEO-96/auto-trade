'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Play, Activity, CheckCircle2, TrendingUp, TrendingDown, Settings } from 'lucide-react';
import api from '@/lib/api';

export default function BacktestPage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');

    const [form, setForm] = useState({
        symbols: ['BTC/KRW'],
        timeframe: '1h',
        strategy_name: 'james_pro_elite',
        limit: 1000,
        initial_capital: 1000000,
        start_date: '',
        end_date: '',
    });
    const [useDateRange, setUseDateRange] = useState(false);

    const toggleSymbol = (symbol: string) => {
        setForm(prev => {
            const symbols = prev.symbols.includes(symbol)
                ? prev.symbols.filter(s => s !== symbol)
                : [...prev.symbols, symbol];
            return { ...prev, symbols: symbols.length > 0 ? symbols : prev.symbols };
        });
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const pollStatus = async (taskId: string) => {
        const interval = setInterval(async () => {
            try {
                const res = await api.get(`/backtest/status/${taskId}`);
                const { status, progress: prog, message, result: resData } = res.data;

                setProgress(prog);
                setProgressMessage(message);

                if (status === 'completed') {
                    clearInterval(interval);
                    setResult(resData);
                    setLoading(false);
                } else if (status === 'failed') {
                    clearInterval(interval);
                    setError(message || '백테스트 중 오류가 발생했습니다.');
                    setLoading(false);
                }
            } catch (err) {
                clearInterval(interval);
                setError('상태 확인 중 오류가 발생했습니다.');
                setLoading(false);
            }
        }, 1000);
    };

    const runBacktest = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);
        setProgress(0);
        setProgressMessage('백테스트 작업을 시작합니다...');

        try {
            const res = await api.post('/backtest/portfolio', {
                symbols: form.symbols,
                timeframe: form.timeframe,
                strategy_name: form.strategy_name,
                limit: useDateRange ? null : Number(form.limit),
                start_date: useDateRange ? form.start_date : null,
                end_date: useDateRange ? form.end_date : null,
                initial_capital: Number(form.initial_capital)
            });

            if (res.data.status === 'running' && res.data.task_id) {
                pollStatus(res.data.task_id);
            } else if (res.data.status === 'success') {
                setResult(res.data);
                setLoading(false);
            } else {
                setError(res.data.message || '백테스트 중 오류가 발생했습니다.');
                setLoading(false);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || '서버와의 통신에 실패했습니다.');
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-transparent relative overflow-hidden">
            {/* Background Decor */}
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[120px] -z-10 animate-pulse-slow"></div>
            <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-[120px] -z-10 animate-pulse-slow font-inter"></div>
            <div className="absolute inset-0 grid-bg opacity-40 -z-20"></div>

            <div className="p-8 max-w-7xl mx-auto animate-fade-in-up">
                <header className="mb-12">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold mb-4 uppercase tracking-widest">
                        <Activity className="w-3 h-3" /> 전문가 전용 시뮬레이터
                    </div>
                    <h1 className="text-5xl font-black mb-4 tracking-tight text-gradient">전략 백테스팅</h1>
                    <p className="text-lg text-slate-400 max-w-2xl leading-relaxed">
                        모멘텀 돌파 알고리즘의 과거 성과를 정밀 분석합니다. 여러 자산을 결합한 포트폴리오 시뮬레이션으로 안정성을 검증하세요.
                    </p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    {/* Configuration Panel */}
                    <div className="lg:col-span-4">
                        <div className="glass-panel p-8 rounded-3xl relative">
                            <h3 className="text-xl font-bold mb-8 flex items-center gap-3">
                                <div className="p-2.5 rounded-xl bg-primary/10 border border-primary/20 shadow-glow-primary/20">
                                    <Settings className="w-5 h-5 text-primary animate-spin-slow" />
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-white leading-tight">전략 파라미터 구성</span>
                                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Backtest Configuration</span>
                                </div>
                            </h3>

                            <form onSubmit={runBacktest} className="space-y-8">
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-1 h-1 rounded-full bg-primary" />
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider">분석 대상 자산</label>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        {['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'].map(s => (
                                            <button
                                                key={s}
                                                type="button"
                                                onClick={() => toggleSymbol(s)}
                                                className={`py-3.5 rounded-2xl text-[11px] font-black transition-all border-2 relative overflow-hidden group/asset ${form.symbols.includes(s)
                                                    ? 'bg-primary/10 border-primary/40 text-primary shadow-[0_0_20px_rgba(59,130,246,0.15)]'
                                                    : 'bg-slate-900/30 border-white/5 text-slate-500 hover:border-white/10 hover:bg-slate-900/50'
                                                    }`}
                                            >
                                                {form.symbols.includes(s) && (
                                                    <div className="absolute top-0 right-0 w-8 h-8 bg-primary/20 rounded-bl-2xl flex items-center justify-center">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                                                    </div>
                                                )}
                                                <span className="relative z-10 tracking-tight">{s.split('/')[0]} <span className="opacity-40 text-[9px] ml-0.5">/ KRW</span></span>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-1 h-1 rounded-full bg-primary" />
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider">수행 전략 선택</label>
                                    </div>
                                    <div className="relative group">
                                        <select
                                            name="strategy_name"
                                            value={form.strategy_name}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/40 border-2 border-white/5 rounded-2xl px-5 py-4.5 focus:outline-none focus:border-primary/40 transition-all font-bold text-sm appearance-none text-slate-200 cursor-pointer group-hover:bg-slate-900/60"
                                        >
                                            <option value="james_pro_elite">🚀 모멘텀 PRO (초고수익형)</option>
                                            <option value="james_pro_stable">🛡️ 모멘텀 PRO (안정형)</option>
                                            <option value="james_pro_aggressive">⚔️ 모멘텀 PRO (공격형)</option>
                                            <option value="james_basic">🌑 모멘텀 돌파 (기본)</option>
                                        </select>
                                        <div className="absolute right-5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500 group-hover:text-primary transition-colors">
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
                                            </svg>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-1 h-1 rounded-full bg-primary" />
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider">캔들 분석 주기</label>
                                    </div>
                                    <div className="grid grid-cols-4 gap-2 bg-slate-950/40 p-1.5 rounded-2xl border-2 border-white/5">
                                        {['15m', '1h', '4h', '1d'].map(tf => (
                                            <button
                                                key={tf}
                                                type="button"
                                                onClick={() => setForm({ ...form, timeframe: tf })}
                                                className={`py-2.5 text-[11px] font-black rounded-xl transition-all ${form.timeframe === tf
                                                    ? 'bg-primary text-white shadow-glow-primary/30'
                                                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                                    }`}
                                            >
                                                {tf === '15m' ? '15분' : tf === '1h' ? '1시간' : tf === '4h' ? '4시간' : '1일'}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-5">
                                    <div className="p-1.5 bg-slate-950/60 rounded-2xl border-2 border-white/5 flex gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setUseDateRange(false)}
                                            className={`flex-1 py-3 text-[11px] font-black rounded-xl transition-all ${!useDateRange ? 'bg-slate-800 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                                        >
                                            캔들 갯수
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setUseDateRange(true)}
                                            className={`flex-1 py-3 text-[11px] font-black rounded-xl transition-all ${useDateRange ? 'bg-slate-800 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                                        >
                                            기간 지정
                                        </button>
                                    </div>

                                    {!useDateRange ? (
                                        <div className="space-y-4 px-1">
                                            <div className="flex justify-between items-end">
                                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">데이터 로드 범위</label>
                                                <span className="text-sm font-black text-primary font-mono tracking-tighter">
                                                    {form.limit.toLocaleString()}<span className="text-[10px] ml-1 opacity-60">CANDLES</span>
                                                </span>
                                            </div>
                                            <div className="relative pt-2">
                                                <input
                                                    type="range"
                                                    name="limit"
                                                    value={form.limit}
                                                    onChange={handleChange}
                                                    min="100"
                                                    max="10000"
                                                    step="100"
                                                    className="w-full accent-primary h-1.5 bg-slate-800/50 rounded-full appearance-none cursor-pointer"
                                                />
                                                <div className="flex justify-between mt-3 text-[9px] font-bold text-slate-600 uppercase tracking-tighter">
                                                    <span>Min 100</span>
                                                    <span>Max 10,000</span>
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-1 gap-4">
                                            <div className="space-y-2">
                                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">시작일</label>
                                                <input
                                                    type="date"
                                                    name="start_date"
                                                    value={form.start_date}
                                                    onChange={handleChange}
                                                    className="w-full bg-slate-900/40 border-2 border-white/5 rounded-2xl px-5 py-3.5 text-sm font-bold text-slate-200 focus:border-primary/40 outline-none transition-all"
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">종료일</label>
                                                <input
                                                    type="date"
                                                    name="end_date"
                                                    value={form.end_date}
                                                    onChange={handleChange}
                                                    className="w-full bg-slate-900/40 border-2 border-white/5 rounded-2xl px-5 py-3.5 text-sm font-bold text-slate-200 focus:border-primary/40 outline-none transition-all"
                                                />
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-4 pt-6 border-t border-white/5">
                                    <div className="flex flex-col gap-1 px-1">
                                        <div className="flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-glow-primary" />
                                            <label className="text-sm font-bold text-slate-200">초기 투자금 설정</label>
                                        </div>
                                        <div className="flex justify-between items-center text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">
                                            <span>Simulated Capital</span>
                                            <span className="text-primary/60">Available: KRW</span>
                                        </div>
                                    </div>

                                    <div className="relative group">
                                        <div className="absolute left-6 top-1/2 -translate-y-1/2 font-black text-slate-500 group-focus-within:text-primary transition-colors text-xl">₩</div>
                                        <input
                                            type="text"
                                            inputMode="numeric"
                                            name="initial_capital"
                                            value={Number(form.initial_capital).toLocaleString()}
                                            onChange={(e) => {
                                                const val = e.target.value.replace(/[^0-9]/g, '');
                                                setForm({ ...form, initial_capital: val ? Number(val) : 0 });
                                            }}
                                            className="w-full bg-slate-900/40 border-2 border-white/5 rounded-2xl pl-14 pr-6 py-5 text-2xl font-black text-white focus:border-primary/40 focus:bg-slate-900/60 outline-none transition-all font-mono tracking-tight"
                                            placeholder="0"
                                        />
                                    </div>

                                    <div className="p-4 rounded-2xl bg-slate-950/40 border border-white/5 flex flex-col gap-1 animate-fade-in">
                                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">포맷팅 미리보기</span>
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-lg font-black text-primary font-mono tracking-tighter">
                                                {Number(form.initial_capital).toLocaleString()}
                                            </span>
                                            <span className="text-xs font-bold text-slate-400">원 (KRW)</span>
                                        </div>
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className={`w-full py-6 rounded-3xl bg-primary hover:bg-primary-dark text-white font-black text-lg transition-all shadow-glow-primary active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 flex items-center justify-center gap-4 relative overflow-hidden group/btn ${loading ? 'grayscale' : ''}`}
                                >
                                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover/btn:animate-shimmer" />
                                    {loading ? (
                                        <div className="w-6 h-6 border-4 border-white/20 border-t-white rounded-full animate-spin"></div>
                                    ) : (
                                        <><Play className="w-6 h-6 fill-white" /> 백테스트 가동하기</>
                                    )}
                                </button>
                            </form>
                        </div>
                    </div>

                    {/* Results Panel */}
                    <div className="lg:col-span-8 flex flex-col gap-8">
                        {error && (
                            <div className="glass-panel p-6 rounded-2xl border-rose-500/20 bg-rose-500/5 text-rose-400 font-bold flex items-center gap-3">
                                <div>{error}</div>
                            </div>
                        )}

                        {loading && (
                            <div className="glass-panel flex-1 rounded-3xl flex flex-col p-8 space-y-8 min-h-[500px]">
                                <div className="flex justify-between items-center">
                                    <div className="space-y-2">
                                        <div className="h-6 w-48 bg-slate-800 animate-pulse rounded-lg"></div>
                                        <div className="h-4 w-32 bg-slate-900 animate-pulse rounded-lg"></div>
                                    </div>
                                    <div className="h-10 w-24 bg-primary/20 animate-pulse rounded-xl"></div>
                                </div>
                                <div className="flex-1 w-full relative flex items-center justify-center border-2 border-dashed border-white/5 rounded-2xl bg-slate-950/20 overflow-hidden">
                                    <div className="absolute inset-0 bg-grid-slate-900/[0.04] bg-[center_top]"></div>
                                    <div className="relative z-10 flex flex-col items-center gap-4">
                                        <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                                        <div className="text-center">
                                            <p className="text-xl font-black text-white mb-1">{Math.round(progress)}%</p>
                                            <p className="text-sm font-bold text-primary animate-pulse">{progressMessage}</p>
                                        </div>
                                    </div>
                                    {/* Abstract background chart skeleton */}
                                    <svg className="absolute bottom-0 left-0 w-full h-1/2 opacity-10" viewBox="0 0 1000 300" preserveAspectRatio="none">
                                        <path d="M0 300 L100 250 L200 280 L300 220 L400 240 L500 180 L600 200 L700 150 L800 170 L900 100 L1000 120 V300 H0 Z" fill="currentColor" className="text-primary animate-pulse" />
                                    </svg>
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    {[1, 2, 3].map(i => (
                                        <div key={i} className="h-24 bg-slate-900/50 rounded-2xl animate-pulse"></div>
                                    ))}
                                </div>
                            </div>
                        )}


                        {!result && !loading ? (
                            <div className="glass-panel flex-1 rounded-3xl flex flex-col items-center justify-center p-20 text-center space-y-6">
                                <div className="p-8 rounded-full bg-slate-900/50 border-2 border-dashed border-white/10 animate-pulse-slow">
                                    <Activity className="w-16 h-16 text-slate-600" />
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-2xl font-bold text-slate-200">데이터 분석 대기 중</h3>
                                    <p className="text-slate-500 max-w-sm mx-auto">전략을 설정하고 실행 버튼을 눌러 과거 성과 시뮬레이션을 시작하세요.</p>
                                </div>
                            </div>
                        ) : result && (
                            <>
                                {/* Performance Overview */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
                                    <div className="glass-panel p-6 md:p-8 rounded-3xl group">
                                        <div className="text-[10px] md:text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">누적 순수익</div>
                                        <div className={`text-xl md:text-2xl lg:text-3xl font-black mb-2 break-all ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-rose-500'}`}>
                                            ₩{(result.final_capital - result.initial_capital).toLocaleString()}
                                        </div>
                                        <div className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg ${result.final_capital >= result.initial_capital ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-500'}`}>
                                            {result.final_capital >= result.initial_capital ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                            {(((result.final_capital - result.initial_capital) / result.initial_capital) * 100).toFixed(2)}%
                                        </div>
                                    </div>

                                    <div className="glass-panel p-6 md:p-8 rounded-3xl">
                                        <div className="text-[10px] md:text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">최종 자산 합계</div>
                                        <div className="text-xl md:text-2xl lg:text-3xl font-black text-white mb-2 break-all">
                                            ₩{result.final_capital.toLocaleString()}
                                        </div>
                                        <div className="text-xs font-bold text-slate-400">전체 자산 성장률</div>
                                    </div>

                                    <div className="glass-panel p-6 md:p-8 rounded-3xl sm:col-span-2 xl:col-span-1">
                                        <div className="text-[10px] md:text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">매매 거래 통계</div>
                                        <div className="text-xl md:text-2xl lg:text-3xl font-black text-primary mb-2">
                                            {result.total_trades} <span className="text-sm md:text-lg font-bold text-slate-500">회 매매</span>
                                        </div>
                                        <div className="text-xs font-bold text-slate-400">포트폴리오 전체 활동건수</div>
                                    </div>
                                </div>

                                {/* Equity Curve Chart */}
                                {result.equity_curve && result.equity_curve.length > 0 && (
                                    <div className="glass-panel p-8 rounded-3xl overflow-hidden border border-white/5 bg-slate-950/20">
                                        <div className="flex justify-between items-center mb-8">
                                            <h3 className="text-xl font-bold flex items-center gap-3">
                                                <TrendingUp className="w-5 h-5 text-primary" />
                                                자산 성장 추이
                                            </h3>
                                            <div className="flex gap-4">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-3 h-3 rounded-full bg-primary shadow-glow-primary"></div>
                                                    <span className="text-xs font-bold text-slate-400">포트폴리오 가치</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="h-[300px] w-full relative group/chart">
                                            <EquityCurveChart data={result.equity_curve} />
                                        </div>
                                    </div>
                                )}


                                {/* Detailed History Table */}
                                <div className="glass-panel rounded-3xl overflow-hidden border border-white/5">
                                    <div className="p-8 border-b border-white/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-slate-950/20">
                                        <h3 className="text-xl font-bold flex items-center gap-3">
                                            <div className="p-2 rounded-lg bg-emerald-500/10">
                                                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                            </div>
                                            상세 매매 이력
                                        </h3>
                                        <div className="text-xs font-bold px-4 py-2 rounded-xl bg-slate-900/80 border border-white/10 text-slate-400 backdrop-blur-sm">
                                            최근 <span className="text-primary">{result.trades.length}건</span>의 거래 기록
                                        </div>
                                    </div>

                                    <div className="overflow-x-auto custom-scrollbar">
                                        <table className="w-full border-collapse">
                                            <thead>
                                                <tr className="bg-slate-950/50 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 border-b border-white/5">
                                                    <th className="px-8 py-5 text-left min-w-[140px]">일시</th>
                                                    <th className="px-8 py-5 text-left min-w-[120px]">종목명</th>
                                                    <th className="px-8 py-5 text-center min-w-[100px]">매매구분</th>
                                                    <th className="px-8 py-5 text-right min-w-[140px]">정산가격</th>
                                                    <th className="px-8 py-5 text-right min-w-[160px]">수익금 (잔액)</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {result.trades.map((trade: any, idx: number) => (
                                                    <tr key={idx} className="hover:bg-primary/5 transition-all duration-300 group">
                                                        <td className="px-8 py-6">
                                                            <div className="text-xs font-bold text-slate-300">
                                                                {new Date(trade.time).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '.').replace(/\.$/, '')}
                                                            </div>
                                                            <div className="text-[10px] font-medium text-slate-500 mt-1 uppercase">
                                                                {new Date(trade.time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                                                            </div>
                                                        </td>
                                                        <td className="px-8 py-6">
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center text-[10px] font-black text-white border border-white/10 group-hover:border-primary/50 transition-colors">
                                                                    {trade.symbol?.charAt(0)}
                                                                </div>
                                                                <span className="font-black text-white tracking-tight">{trade.symbol?.split('/')[0]}</span>
                                                            </div>
                                                        </td>
                                                        <td className="px-8 py-6 text-center">
                                                            <div className="flex justify-center">
                                                                <span className={`inline-flex items-center justify-center w-16 py-1.5 rounded-lg text-[10px] font-black border-2 whitespace-nowrap shadow-sm ${trade.side === 'BUY'
                                                                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                                                    : 'bg-rose-500/10 border-rose-500/20 text-rose-500'
                                                                    }`}>
                                                                    {trade.side === 'BUY' ? '매수' : '매도'}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="px-8 py-6 text-right font-black text-slate-200 font-mono tracking-tighter">
                                                            ₩{trade.price.toLocaleString()}
                                                        </td>
                                                        <td className={`px-8 py-6 text-right group-hover:scale-105 transition-transform duration-300 origin-right`}>
                                                            <div className={`text-sm font-black font-mono tracking-tighter ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-rose-500' : 'text-slate-500'}`}>
                                                                {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${trade.pnl.toLocaleString()}` : `-₩${Math.abs(trade.pnl).toLocaleString()}`) : '-'}
                                                            </div>
                                                            <div className="text-[10px] font-bold text-slate-500 opacity-60 font-mono mt-1">
                                                                ₩{trade.capital.toLocaleString()}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                            </>
                        )}
                    </div>
                </div>
            </div>
        </div >
    );
}

function EquityCurveChart({ data }: { data: { time: string, value: number }[] }) {
    if (!data || data.length === 0) return null;

    const values = data.map(d => d.value);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const range = maxVal - minVal || 1;
    const padding = range * 0.1;

    const chartMax = maxVal + padding;
    const chartMin = Math.max(0, minVal - padding);
    const chartRange = chartMax - chartMin;

    const width = 1000;
    const height = 300;

    const points = data.map((d, i) => ({
        x: (i / (data.length - 1)) * width,
        y: height - ((d.value - chartMin) / chartRange) * height
    }));

    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`;

    const [hoverIndex, setHoverIndex] = useState<number | null>(null);
    const [pathLength, setPathLength] = useState(0);
    const pathRef = useRef<SVGPathElement>(null);

    useEffect(() => {
        if (pathRef.current) {
            setPathLength(pathRef.current.getTotalLength());
        }
    }, [data]);

    // Animation duration based on data points (min 1.5s, max 4s)
    const animationDuration = Math.max(1.5, Math.min(4, data.length / 500));

    return (
        <div className="relative w-full h-full">
            <svg
                viewBox={`0 0 ${width} ${height}`}
                className="w-full h-full overflow-visible"
                preserveAspectRatio="none"
                onMouseMove={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const x = ((e.clientX - rect.left) / rect.width) * width;
                    const index = Math.round((x / width) * (data.length - 1));
                    setHoverIndex(Math.max(0, Math.min(data.length - 1, index)));
                }}
                onMouseLeave={() => setHoverIndex(null)}
            >
                <defs>
                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                    </linearGradient>
                </defs>

                {/* Grid Lines */}
                {[0, 0.25, 0.5, 0.75, 1].map(v => (
                    <line
                        key={v}
                        x1="0" y1={v * height} x2={width} y2={v * height}
                        stroke="rgba(255,255,255,0.05)"
                        strokeWidth="1"
                    />
                ))}

                {/* Area - Fade in after line starts drawing */}
                <path
                    d={areaPath}
                    fill="url(#areaGradient)"
                    className="animate-fade-in"
                    style={{ animationDelay: '0.5s', animationFillMode: 'both' }}
                />

                {/* Line with Drawing Animation */}
                <path
                    ref={pathRef}
                    d={linePath}
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                    style={{
                        strokeDasharray: pathLength,
                        strokeDashoffset: pathLength,
                        animation: `drawPath ${animationDuration}s cubic-bezier(0.4, 0, 0.2, 1) forwards`,
                    }}
                />

                {/* Hover Line & Point */}
                {hoverIndex !== null && (
                    <>
                        <line
                            x1={points[hoverIndex].x} y1="0"
                            x2={points[hoverIndex].x} y2={height}
                            stroke="rgba(255,255,255,0.2)"
                            strokeWidth="1"
                            strokeDasharray="4 4"
                        />
                        <circle
                            cx={points[hoverIndex].x}
                            cy={points[hoverIndex].y}
                            r="6"
                            fill="#3b82f6"
                            stroke="white"
                            strokeWidth="2"
                            className="drop-shadow-glow-primary"
                        />
                    </>
                )}
            </svg>

            <style jsx>{`
                @keyframes drawPath {
                    from { stroke-dashoffset: var(--path-length, 2000); }
                    to { stroke-dashoffset: 0; }
                }
                path {
                    --path-length: ${pathLength};
                }
            `}</style>

            {/* Tooltip */}
            {hoverIndex !== null && (
                <div
                    className="absolute z-10 p-4 rounded-2xl bg-slate-900/95 border border-white/10 backdrop-blur-md shadow-2xl pointer-events-none"
                    style={{
                        left: `${(hoverIndex / (data.length - 1)) * 100}%`,
                        top: `${(points[hoverIndex].y / height) * 100}%`,
                        transform: `translate(${hoverIndex > data.length / 2 ? '-110%' : '10%'}, -50%)`
                    }}
                >
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
                        {new Date(data[hoverIndex].time).toLocaleString()}
                    </div>
                    <div className="text-xl font-black text-white">
                        ₩{data[hoverIndex].value.toLocaleString()}
                    </div>
                    <div className={`text-xs font-bold flex items-center gap-1 ${data[hoverIndex].value >= data[0].value ? 'text-emerald-400' : 'text-rose-500'}`}>
                        {data[hoverIndex].value >= data[0].value ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {Math.abs(((data[hoverIndex].value - data[0].value) / data[0].value) * 100).toFixed(2)}%
                    </div>
                </div>
            )}
        </div>
    );
}
