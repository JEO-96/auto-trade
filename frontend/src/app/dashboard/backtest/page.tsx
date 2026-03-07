'use client';
import { useState } from 'react';
import { Play, Activity, CheckCircle2, AlertTriangle, TrendingUp, TrendingDown, DollarSign, Settings } from 'lucide-react';
import api from '@/lib/api';
import StatCard from '@/components/ui/StatCard';

export default function BacktestPage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const [form, setForm] = useState({
        symbols: ['BTC/KRW'],
        timeframe: '1h',
        strategy_name: 'james_pro',
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

    const runBacktest = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

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

            if (res.data.status === 'success') {
                setResult(res.data);
            } else {
                setError(res.data.message || '백테스트 중 오류가 발생했습니다.');
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || '서버와의 통신에 실패했습니다.');
        } finally {
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
                                <div className="p-2 rounded-xl bg-primary/10">
                                    <Settings className="w-5 h-5 text-primary" />
                                </div>
                                전략 파라미터 구성
                            </h3>

                            <form onSubmit={runBacktest} className="space-y-6">
                                <div className="space-y-3">
                                    <label className="text-sm font-semibold text-slate-300 ml-1">분석 대상 자산</label>
                                    <div className="grid grid-cols-2 gap-3">
                                        {['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'].map(s => (
                                            <button
                                                key={s}
                                                type="button"
                                                onClick={() => toggleSymbol(s)}
                                                className={`py-3 rounded-xl text-xs font-bold transition-all border-2 ${form.symbols.includes(s)
                                                    ? 'bg-primary/10 border-primary/50 text-primary shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                                    : 'bg-slate-900/50 border-white/5 text-slate-500 hover:border-white/20'
                                                    }`}
                                            >
                                                {s.split('/')[0]}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-semibold text-slate-300 ml-1">수행 전략 선택</label>
                                    <select
                                        name="strategy_name"
                                        value={form.strategy_name}
                                        onChange={handleChange}
                                        className="w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl px-5 py-4 focus:outline-none focus:border-primary/50 transition-all font-bold text-sm appearance-none"
                                    >
                                        <option value="james_pro_stable">🛡️ 모멘텀 PRO (안정형)</option>
                                        <option value="james_pro_aggressive">⚔️ 모멘텀 PRO (공격형)</option>
                                        <option value="james_basic">🌑 모멘텀 돌파 (기본)</option>
                                    </select>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-semibold text-slate-300 ml-1">캔들 분석 주기</label>
                                    <div className="grid grid-cols-4 gap-2 bg-slate-900/50 p-1.5 rounded-2xl border-2 border-white/5">
                                        {['15m', '1h', '4h', '1d'].map(tf => (
                                            <button
                                                key={tf}
                                                type="button"
                                                onClick={() => setForm({ ...form, timeframe: tf })}
                                                className={`py-2 text-xs font-bold rounded-xl transition-all ${form.timeframe === tf
                                                    ? 'bg-primary text-white shadow-lg'
                                                    : 'text-slate-500 hover:text-slate-300'
                                                    }`}
                                            >
                                                {tf === '15m' ? '15분' : tf === '1h' ? '1시간' : tf === '4h' ? '4시간' : '1일'}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="p-1.5 bg-slate-950/50 rounded-2xl border-2 border-white/5 flex gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setUseDateRange(false)}
                                        className={`flex-1 py-2.5 text-xs font-bold rounded-xl transition-all ${!useDateRange ? 'bg-slate-800 text-white shadow-inner' : 'text-slate-500'}`}
                                    >
                                        캔들 갯수
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setUseDateRange(true)}
                                        className={`flex-1 py-2.5 text-xs font-bold rounded-xl transition-all ${useDateRange ? 'bg-slate-800 text-white shadow-inner' : 'text-slate-500'}`}
                                    >
                                        기간 지정
                                    </button>
                                </div>

                                {!useDateRange ? (
                                    <div className="space-y-2">
                                        <div className="flex justify-between px-1">
                                            <label className="text-sm font-semibold text-slate-300">데이터 로드 범위</label>
                                            <span className="text-xs font-mono text-primary">최근 {form.limit.toLocaleString()}개 캔들</span>
                                        </div>
                                        <input
                                            type="range"
                                            name="limit"
                                            value={form.limit}
                                            onChange={handleChange}
                                            min="100"
                                            max="10000"
                                            step="100"
                                            className="w-full accent-primary h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                                        />
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 gap-4">
                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-slate-500 uppercase ml-1">시작일</label>
                                            <input
                                                type="date"
                                                name="start_date"
                                                value={form.start_date}
                                                onChange={handleChange}
                                                className="w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl px-5 py-3 text-sm font-bold text-slate-200 focus:border-primary/50 outline-none"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-slate-500 uppercase ml-1">종료일</label>
                                            <input
                                                type="date"
                                                name="end_date"
                                                value={form.end_date}
                                                onChange={handleChange}
                                                className="w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl px-5 py-3 text-sm font-bold text-slate-200 focus:border-primary/50 outline-none"
                                            />
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-2 pt-2">
                                    <label className="text-sm font-semibold text-slate-300 ml-1">시뮬레이션 투자금</label>
                                    <div className="relative">
                                        <span className="absolute left-4 top-1/2 -translate-y-1/2 font-bold text-slate-500">₩</span>
                                        <input
                                            type="number"
                                            name="initial_capital"
                                            value={form.initial_capital}
                                            onChange={handleChange}
                                            className="w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl pl-10 pr-6 py-4 text-lg font-black text-white focus:border-primary/50 outline-none"
                                        />
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className={`w-full glow-btn primary-gradient py-5 rounded-2xl font-black text-white text-lg flex items-center justify-center gap-3 shadow-[0_10px_30px_rgba(37,99,235,0.3)] hover:-translate-y-1 active:translate-y-0.5 transition-all duration-300 ${loading ? 'opacity-50 grayscale cursor-not-allowed' : ''}`}
                                >
                                    {loading ? (
                                        <div className="w-6 h-6 border-4 border-white/20 border-t-white rounded-full animate-spin"></div>
                                    ) : (
                                        <><Play className="fill-current w-5 h-5" /> 백테스트 가동하기</>
                                    )}
                                </button>
                            </form>
                        </div>
                    </div>

                    {/* Results Panel */}
                    <div className="lg:col-span-8 flex flex-col gap-8">
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
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div className="glass-panel p-8 rounded-3xl group">
                                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">누적 순수익</div>
                                        <div className={`text-3xl font-black mb-2 ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-rose-500'}`}>
                                            ₩{(result.final_capital - result.initial_capital).toLocaleString()}
                                        </div>
                                        <div className={`inline-flex items-center gap-1 text-sm font-bold px-2 py-1 rounded-lg ${result.final_capital >= result.initial_capital ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-500'}`}>
                                            {result.final_capital >= result.initial_capital ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                            {(((result.final_capital - result.initial_capital) / result.initial_capital) * 100).toFixed(2)}%
                                        </div>
                                    </div>

                                    <div className="glass-panel p-8 rounded-3xl">
                                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">최종 자산 합계</div>
                                        <div className="text-3xl font-black text-white mb-2">
                                            ₩{result.final_capital.toLocaleString()}
                                        </div>
                                        <div className="text-xs font-bold text-slate-400">전체 자산 성장률</div>
                                    </div>

                                    <div className="glass-panel p-8 rounded-3xl">
                                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">매매 거래 통계</div>
                                        <div className="text-3xl font-black text-primary mb-2">
                                            {result.total_trades} <span className="text-lg font-bold text-slate-500">회 매매</span>
                                        </div>
                                        <div className="text-xs font-bold text-slate-400">포트폴리오 전체 활동건수</div>
                                    </div>
                                </div>

                                {/* Detailed History Table */}
                                <div className="glass-panel rounded-3xl overflow-hidden">
                                    <div className="p-8 border-b border-white/5 flex justify-between items-center">
                                        <h3 className="text-xl font-bold flex items-center gap-3">
                                            <CheckCircle2 className="w-5 h-5 text-emerald-400" /> 상세 매매 이력
                                        </h3>
                                        <div className="text-xs font-bold px-3 py-1.5 rounded-full bg-slate-900 border border-white/5 text-slate-400">
                                            최근 {result.trades.length}건의 거래 기록
                                        </div>
                                    </div>

                                    <div className="overflow-x-auto">
                                        <table className="w-full">
                                            <thead>
                                                <tr className="bg-slate-950/30 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 border-b border-white/5">
                                                    <th className="px-8 py-5 text-left">일시</th>
                                                    <th className="px-8 py-5 text-left">종목명</th>
                                                    <th className="px-8 py-5 text-left">매매구분</th>
                                                    <th className="px-8 py-5 text-right">정산가격</th>
                                                    <th className="px-8 py-5 text-right">수익금 (잔액)</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {result.trades.map((trade: any, idx: number) => (
                                                    <tr key={idx} className="hover:bg-primary/5 transition-all duration-300 group">
                                                        <td className="px-8 py-6 text-xs font-bold text-slate-400">
                                                            {new Date(trade.time).toLocaleDateString()}
                                                            <span className="ml-2 opacity-50 block text-[10px] font-medium">{new Date(trade.time).toLocaleTimeString()}</span>
                                                        </td>
                                                        <td className="px-8 py-6">
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-black text-white border border-white/10">
                                                                    {trade.symbol?.charAt(0)}
                                                                </div>
                                                                <span className="font-black text-white">{trade.symbol?.split('/')[0]}</span>
                                                            </div>
                                                        </td>
                                                        <td className="px-8 py-6">
                                                            <span className={`px-4 py-1.5 rounded-full text-[10px] font-black border-2 ${trade.side === 'BUY'
                                                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                                                : 'bg-rose-500/10 border-rose-500/20 text-rose-500'
                                                                }`}>
                                                                {trade.side === 'BUY' ? '매수' : '매도'}
                                                            </span>
                                                        </td>
                                                        <td className="px-8 py-6 text-right font-black text-slate-200">
                                                            ₩{trade.price.toLocaleString()}
                                                        </td>
                                                        <td className={`px-8 py-6 text-right font-black ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-rose-500' : 'text-slate-500'}`}>
                                                            {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${trade.pnl.toLocaleString()}` : `-₩${Math.abs(trade.pnl).toLocaleString()}`) : '-'}
                                                            <div className="text-[10px] font-bold text-slate-500 opacity-60">
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
        </div>
    );
}
