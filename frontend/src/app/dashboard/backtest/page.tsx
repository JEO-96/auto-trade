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
        <div className="p-8 max-w-6xl mx-auto animate-fade-in-up">
            <header className="mb-8">
                <h1 className="text-3xl font-bold mb-2">전략 백테스팅</h1>
                <p className="text-gray-400">여러 코인을 동시에 돌리는 포트폴리오 시뮬레이션을 수행합니다.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Configuration Panel */}
                <div className="lg:col-span-1">
                    <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-24 h-24 bg-primary/10 rounded-bl-full -z-10"></div>
                        <h3 className="text-xl font-bold mb-6 flex items-center gap-2"><Settings className="w-5 h-5 text-primary" /> 파라미터 설정</h3>

                        <form onSubmit={runBacktest} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-2">감시 대상 코인 (Symbols)</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'].map(s => (
                                        <button
                                            key={s}
                                            type="button"
                                            onClick={() => toggleSymbol(s)}
                                            className={`px-3 py-2 rounded-lg text-xs font-mono transition-all border ${form.symbols.includes(s) ? 'bg-primary/20 border-primary text-primary' : 'bg-surface/50 border-gray-700/50 text-gray-400 hover:border-gray-500'}`}
                                        >
                                            {s.split('/')[0]}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1">사용 전략</label>
                                <select
                                    name="strategy_name"
                                    value={form.strategy_name}
                                    onChange={handleChange}
                                    className="w-full bg-surface/50 border border-gray-700/50 rounded-lg px-4 py-3 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                >
                                    <option value="james_pro_stable">모멘텀 돌파 PRO (안정형 - 하락장 방어)</option>
                                    <option value="james_pro_aggressive">모멘텀 돌파 PRO (공격형 - 수익 극대화)</option>
                                    <option value="james_basic">모멘텀 돌파 (기본)</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1">타임프레임</label>
                                <select
                                    name="timeframe"
                                    value={form.timeframe}
                                    onChange={handleChange}
                                    className="w-full bg-surface/50 border border-gray-700/50 rounded-lg px-4 py-3 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                >
                                    <option value="15m">15분봉</option>
                                    <option value="1h" selected>1시간봉</option>
                                    <option value="4h">4시간봉</option>
                                    <option value="1d">일봉</option>
                                </select>
                            </div>

                            <div className="flex bg-surface/30 p-1 rounded-lg border border-gray-700/50 mb-2">
                                <button
                                    type="button"
                                    onClick={() => setUseDateRange(false)}
                                    className={`flex-1 py-1.5 text-xs rounded-md transition-all ${!useDateRange ? 'bg-primary text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    갯수 기준
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setUseDateRange(true)}
                                    className={`flex-1 py-1.5 text-xs rounded-md transition-all ${useDateRange ? 'bg-primary text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    기간 기준
                                </button>
                            </div>

                            {!useDateRange ? (
                                <div>
                                    <div className="flex justify-between items-center mb-1">
                                        <label className="block text-sm font-medium text-gray-400">과거 캔들 갯수 (Limit)</label>
                                        <span className="text-[10px] text-primary/70">최대 30,000</span>
                                    </div>
                                    <input
                                        type="number"
                                        name="limit"
                                        value={form.limit}
                                        onChange={handleChange}
                                        min="100"
                                        max="30000"
                                        className="w-full bg-surface/50 border border-gray-700/50 rounded-lg px-4 py-3 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                    />
                                    <div className="mt-2 flex gap-2">
                                        {[1, 3, 6].map(m => (
                                            <button
                                                key={m}
                                                type="button"
                                                onClick={() => {
                                                    const perMonth = form.timeframe === '15m' ? 2880 : form.timeframe === '1h' ? 720 : form.timeframe === '4h' ? 180 : 30;
                                                    setForm({ ...form, limit: perMonth * m });
                                                }}
                                                className="text-[10px] px-2 py-1 bg-surface border border-gray-700 rounded hover:border-primary/50 transition-colors"
                                            >
                                                {m}개월
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-400 mb-1">시작일</label>
                                        <input
                                            type="date"
                                            name="start_date"
                                            value={form.start_date}
                                            onChange={handleChange}
                                            className="w-full bg-surface/50 border border-gray-700/50 rounded-lg px-4 py-3 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-400 mb-1">종료일 (선택)</label>
                                        <input
                                            type="date"
                                            name="end_date"
                                            value={form.end_date}
                                            onChange={handleChange}
                                            className="w-full bg-surface/50 border border-gray-700/50 rounded-lg px-4 py-3 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                        />
                                    </div>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1">총 투자 원금 (KRW)</label>
                                <input
                                    type="number"
                                    name="initial_capital"
                                    value={form.initial_capital}
                                    onChange={handleChange}
                                    min="10000"
                                    className="w-full bg-surface/50 border border-gray-700/50 rounded-lg px-4 py-3 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className={`w-full mt-4 flex items-center justify-center gap-2 py-4 rounded-xl font-bold shadow-lg transition-all ${loading ? 'bg-primary/50 text-white/70 cursor-not-allowed' : 'bg-primary hover:bg-blue-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]'}`}
                            >
                                {loading ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        포트폴리오 시뮬레이션 중...
                                    </>
                                ) : (
                                    <>
                                        <Play className="w-5 h-5" /> 백테스트 실행하기
                                    </>
                                )}
                            </button>

                            {error && (
                                <div className="mt-4 flex items-start gap-2 text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20 text-sm">
                                    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                    <p>{error}</p>
                                </div>
                            )}
                        </form>
                    </div>
                </div>

                {/* Results Panel */}
                <div className="lg:col-span-2 space-y-6">
                    {!result && !loading && (
                        <div className="glass-panel p-12 rounded-2xl h-full flex flex-col items-center justify-center text-center border-dashed border-2 border-gray-700/50 bg-surface/10">
                            <Activity className="w-16 h-16 text-gray-600 mb-4" />
                            <h3 className="text-xl font-bold text-gray-400 mb-2">포트폴리오 백테스트 결과 대기중</h3>
                            <p className="text-sm text-gray-500 max-w-md">여러 코인을 동시에 돌렸을 때의 통합 수익률과 리스크 분산 효과를 확인해 보세요.</p>
                        </div>
                    )}

                    {result && (
                        <>
                            {/* Key Metrics */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <StatCard
                                    title="전체 최종 자산"
                                    value={`₩${result.final_capital.toLocaleString()}`}
                                    accentColor="bg-primary/5"
                                    subtitle={
                                        <div className="flex items-center gap-1 mt-2 text-sm">
                                            {result.final_capital >= result.initial_capital ? (
                                                <TrendingUp className="w-4 h-4 text-emerald-400" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 text-red-500" />
                                            )}
                                            <span className={result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-500'}>
                                                {(((result.final_capital - result.initial_capital) / result.initial_capital) * 100).toFixed(2)}%
                                            </span>
                                        </div>
                                    }
                                />

                                <StatCard
                                    title="포트폴리오 PnL"
                                    value={
                                        <span className={result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-500'}>
                                            {result.final_capital >= result.initial_capital ? '+' : ''}
                                            ₩{(result.final_capital - result.initial_capital).toLocaleString()}
                                        </span>
                                    }
                                />

                                <StatCard
                                    title="총 거래 (전 종목)"
                                    value={`${result.total_trades} 번`}
                                    icon={<Activity className="w-6 h-6 text-secondary" />}
                                />
                            </div>

                            {/* Trade History */}
                            <div className="glass-panel p-6 rounded-2xl">
                                <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                                    <CheckCircle2 className="w-5 h-5 text-secondary" /> 통합 거래 내역
                                </h3>

                                <div className="overflow-x-auto">
                                    <table className="w-full text-left border-collapse">
                                        <thead>
                                            <tr className="border-b border-gray-800 text-xs uppercase tracking-wider text-gray-400">
                                                <th className="pb-3 pl-2">시간</th>
                                                <th className="pb-3">코인</th>
                                                <th className="pb-3">구분</th>
                                                <th className="pb-3 text-right">가격</th>
                                                <th className="pb-3 text-right">전체 자산</th>
                                                <th className="pb-3 text-right">PnL</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-800/50">
                                            {result.trades.map((trade: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-white/5 transition-colors group">
                                                    <td className="py-4 pl-2 text-sm text-gray-500 whitespace-nowrap">{new Date(trade.time).toLocaleString()}</td>
                                                    <td className="py-4 font-bold text-primary text-sm">{trade.symbol?.split('/')[0]}</td>
                                                    <td className="py-4">
                                                        <span className={`px-2 py-1 rounded-md text-xs font-bold ${trade.side === 'BUY' ? 'bg-primary/20 text-primary' : 'bg-red-500/20 text-red-500'}`}>
                                                            {trade.side}
                                                        </span>
                                                    </td>
                                                    <td className="py-4 text-right font-mono text-gray-300">
                                                        ₩{trade.price.toLocaleString()}
                                                    </td>
                                                    <td className="py-4 text-right font-mono text-white">
                                                        ₩{trade.capital.toLocaleString()}
                                                    </td>
                                                    <td className={`py-4 text-right font-mono text-sm ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                                                        {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${trade.pnl.toLocaleString()}` : `-₩${Math.abs(trade.pnl).toLocaleString()}`) : '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                            {result.trades.length === 0 && (
                                                <tr>
                                                    <td colSpan={6} className="py-8 text-center text-gray-500">
                                                        지정된 기간 동안 거래 조건에 부합하는 시그널이 발생하지 않았습니다.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
