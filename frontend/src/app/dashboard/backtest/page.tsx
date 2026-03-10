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
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, []);

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
        intervalRef.current = setInterval(async () => {
            try {
                const res = await api.get(`/backtest/status/${taskId}`);
                const { status, progress: prog, message, result: resData } = res.data;

                setProgress(prog);
                setProgressMessage(message);

                if (status === 'completed') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setResult(resData);
                    setLoading(false);
                } else if (status === 'failed') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setError(message || '백테스트 중 오류가 발생했습니다.');
                    setLoading(false);
                }
            } catch (err) {
                if (intervalRef.current) clearInterval(intervalRef.current);
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
        <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in-up">
            <header className="mb-8">
                <h1 className="text-2xl font-bold mb-1 text-white">전략 백테스팅</h1>
                <p className="text-sm text-gray-500 max-w-xl">
                    모멘텀 돌파 알고리즘의 과거 성과를 분석하고 포트폴리오 시뮬레이션으로 검증하세요.
                </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Configuration */}
                <div className="lg:col-span-4">
                    <div className="glass-panel p-6 rounded-2xl">
                        <h3 className="text-base font-bold mb-6 flex items-center gap-2.5">
                            <Settings className="w-5 h-5 text-primary" />
                            전략 설정
                        </h3>

                        <form onSubmit={runBacktest} className="space-y-6">
                            {/* Assets */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">분석 대상 자산</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {['BTC/KRW', 'ETH/KRW', 'SOL/KRW', 'XRP/KRW'].map(s => (
                                        <button
                                            key={s}
                                            type="button"
                                            onClick={() => toggleSymbol(s)}
                                            className={`py-2.5 rounded-xl text-xs font-semibold transition-all border ${form.symbols.includes(s)
                                                ? 'bg-primary/10 border-primary/30 text-primary'
                                                : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10'
                                                }`}
                                        >
                                            {s.split('/')[0]} <span className="opacity-40 text-[10px]">/ KRW</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Strategy */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">전략 선택</label>
                                <select
                                    name="strategy_name"
                                    value={form.strategy_name}
                                    onChange={handleChange}
                                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm font-medium text-white appearance-none cursor-pointer focus:border-primary/30 transition-colors"
                                >
                                    <option value="james_pro_elite">모멘텀 PRO (초고수익형)</option>
                                    <option value="james_pro_stable">모멘텀 PRO (안정형)</option>
                                    <option value="james_pro_aggressive">모멘텀 PRO (공격형)</option>
                                    <option value="james_basic">모멘텀 돌파 (기본)</option>
                                </select>
                            </div>

                            {/* Timeframe */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">캔들 주기</label>
                                <div className="grid grid-cols-4 gap-1.5 bg-white/[0.02] p-1 rounded-xl border border-white/[0.04]">
                                    {['15m', '1h', '4h', '1d'].map(tf => (
                                        <button
                                            key={tf}
                                            type="button"
                                            onClick={() => setForm({ ...form, timeframe: tf })}
                                            className={`py-2 text-xs font-semibold rounded-lg transition-all ${form.timeframe === tf
                                                ? 'bg-primary text-white'
                                                : 'text-gray-500 hover:text-gray-300'
                                                }`}
                                        >
                                            {tf === '15m' ? '15분' : tf === '1h' ? '1시간' : tf === '4h' ? '4시간' : '1일'}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Data Range Mode */}
                            <div>
                                <div className="flex gap-1.5 bg-white/[0.02] p-1 rounded-xl border border-white/[0.04] mb-4">
                                    <button
                                        type="button"
                                        onClick={() => setUseDateRange(false)}
                                        className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${!useDateRange ? 'bg-white/[0.08] text-white' : 'text-gray-500'}`}
                                    >
                                        캔들 갯수
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setUseDateRange(true)}
                                        className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${useDateRange ? 'bg-white/[0.08] text-white' : 'text-gray-500'}`}
                                    >
                                        기간 지정
                                    </button>
                                </div>

                                {!useDateRange ? (
                                    <div>
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-xs text-gray-500">데이터 범위</span>
                                            <span className="text-sm font-bold text-primary font-mono">
                                                {form.limit.toLocaleString()}
                                            </span>
                                        </div>
                                        <input
                                            type="range"
                                            name="limit"
                                            value={form.limit}
                                            onChange={handleChange}
                                            min="100"
                                            max="10000"
                                            step="100"
                                            className="w-full accent-primary h-1 bg-white/[0.06] rounded-full appearance-none cursor-pointer"
                                        />
                                        <div className="flex justify-between mt-1.5 text-[10px] text-gray-600">
                                            <span>100</span>
                                            <span>10,000</span>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <div>
                                            <label className="text-xs text-gray-500 font-medium mb-1.5 block">시작일</label>
                                            <input
                                                type="date"
                                                name="start_date"
                                                value={form.start_date}
                                                onChange={handleChange}
                                                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-white focus:border-primary/30 transition-colors"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-gray-500 font-medium mb-1.5 block">종료일</label>
                                            <input
                                                type="date"
                                                name="end_date"
                                                value={form.end_date}
                                                onChange={handleChange}
                                                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-white focus:border-primary/30 transition-colors"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Initial Capital */}
                            <div className="pt-4 border-t border-white/[0.04]">
                                <label className="text-xs text-gray-500 font-medium mb-2 block">초기 투자금</label>
                                <div className="relative">
                                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-semibold">₩</div>
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        name="initial_capital"
                                        value={Number(form.initial_capital).toLocaleString()}
                                        onChange={(e) => {
                                            const val = e.target.value.replace(/[^0-9]/g, '');
                                            setForm({ ...form, initial_capital: val ? Number(val) : 0 });
                                        }}
                                        className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-10 pr-4 py-3 text-lg font-bold text-white focus:border-primary/30 transition-colors font-mono"
                                        placeholder="0"
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-3.5 rounded-xl bg-primary hover:bg-primary-dark text-white font-semibold text-sm transition-all shadow-glow-primary disabled:opacity-40 flex items-center justify-center gap-2"
                            >
                                {loading ? (
                                    <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <><Play className="w-4 h-4 fill-white" /> 백테스트 실행</>
                                )}
                            </button>
                        </form>
                    </div>
                </div>

                {/* Results */}
                <div className="lg:col-span-8 flex flex-col gap-5">
                    {error && (
                        <div className="glass-panel p-4 rounded-xl border-red-500/20 bg-red-500/[0.04] text-red-400 text-sm font-medium">
                            {error}
                        </div>
                    )}

                    {loading && (
                        <div className="glass-panel flex-1 rounded-2xl flex flex-col items-center justify-center p-12 min-h-[400px]">
                            <div className="w-14 h-14 border-2 border-primary/20 border-t-primary rounded-full animate-spin mb-4" />
                            <p className="text-xl font-bold text-white mb-1">{Math.round(progress)}%</p>
                            <p className="text-sm text-primary">{progressMessage}</p>
                        </div>
                    )}

                    {!result && !loading && (
                        <div className="glass-panel flex-1 rounded-2xl flex flex-col items-center justify-center p-16 text-center">
                            <Activity className="w-12 h-12 text-gray-700 mb-4" />
                            <h3 className="text-lg font-semibold text-gray-400 mb-1">분석 대기 중</h3>
                            <p className="text-sm text-gray-600">전략을 설정하고 실행 버튼을 눌러주세요.</p>
                        </div>
                    )}

                    {result && (
                        <>
                            {/* Backtest disclaimer */}
                            <p className="text-xs text-gray-500">
                                * 이 결과는 과거 데이터 시뮬레이션이며 실제 수익을 보장하지 않습니다.
                            </p>

                            {/* Stats */}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div className="glass-panel p-5 rounded-2xl">
                                    <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">누적 수익</p>
                                    <p className={`text-2xl font-bold ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-400'}`}>
                                        ₩{(result.final_capital - result.initial_capital).toLocaleString()}
                                    </p>
                                    <div className={`inline-flex items-center gap-1 text-xs font-medium mt-2 ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {result.final_capital >= result.initial_capital ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                                        {(((result.final_capital - result.initial_capital) / result.initial_capital) * 100).toFixed(2)}%
                                    </div>
                                </div>

                                <div className="glass-panel p-5 rounded-2xl">
                                    <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">최종 자산</p>
                                    <p className="text-2xl font-bold text-white">₩{result.final_capital.toLocaleString()}</p>
                                </div>

                                <div className="glass-panel p-5 rounded-2xl">
                                    <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">매매 횟수</p>
                                    <p className="text-2xl font-bold text-primary">
                                        {result.total_trades}<span className="text-sm text-gray-500 ml-1 font-medium">회</span>
                                    </p>
                                </div>
                            </div>

                            {/* Equity Curve */}
                            {result.equity_curve && result.equity_curve.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl">
                                    <div className="flex justify-between items-center mb-6">
                                        <h3 className="text-base font-bold flex items-center gap-2">
                                            <TrendingUp className="w-4 h-4 text-primary" />
                                            자산 성장 추이
                                        </h3>
                                        <div className="flex items-center gap-2">
                                            <div className="w-2.5 h-2.5 rounded-full bg-primary"></div>
                                            <span className="text-xs text-gray-500">포트폴리오 가치</span>
                                        </div>
                                    </div>
                                    <div className="h-[280px] w-full">
                                        <EquityCurveChart data={result.equity_curve} />
                                    </div>
                                </div>
                            )}

                            {/* Trade History */}
                            <div className="glass-panel rounded-2xl overflow-hidden">
                                <div className="p-5 border-b border-white/[0.04] flex justify-between items-center">
                                    <h3 className="text-base font-bold flex items-center gap-2">
                                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                        매매 이력
                                    </h3>
                                    <span className="text-xs text-gray-500">{result.trades.length}건</span>
                                </div>

                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead>
                                            <tr className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 border-b border-white/[0.04]">
                                                <th className="px-5 py-3 text-left">일시</th>
                                                <th className="px-5 py-3 text-left">종목</th>
                                                <th className="px-5 py-3 text-center">구분</th>
                                                <th className="px-5 py-3 text-right">가격</th>
                                                <th className="px-5 py-3 text-right">수익</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/[0.03]">
                                            {result.trades.map((trade: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-white/[0.02] transition-colors text-sm">
                                                    <td className="px-5 py-4">
                                                        <p className="text-xs text-gray-300">
                                                            {new Date(trade.time).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '.').replace(/\.$/, '')}
                                                        </p>
                                                        <p className="text-[10px] text-gray-600 mt-0.5">
                                                            {new Date(trade.time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                                                        </p>
                                                    </td>
                                                    <td className="px-5 py-4">
                                                        <span className="font-semibold text-white">{trade.symbol?.split('/')[0]}</span>
                                                    </td>
                                                    <td className="px-5 py-4 text-center">
                                                        <span className={`inline-flex px-2.5 py-1 rounded-md text-[10px] font-semibold ${trade.side === 'BUY'
                                                            ? 'bg-emerald-500/10 text-emerald-400'
                                                            : 'bg-red-500/10 text-red-400'
                                                            }`}>
                                                            {trade.side === 'BUY' ? '매수' : '매도'}
                                                        </span>
                                                    </td>
                                                    <td className="px-5 py-4 text-right font-mono text-sm text-gray-300">
                                                        ₩{trade.price.toLocaleString()}
                                                    </td>
                                                    <td className="px-5 py-4 text-right">
                                                        <p className={`font-mono text-sm font-medium ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-600'}`}>
                                                            {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${trade.pnl.toLocaleString()}` : `-₩${Math.abs(trade.pnl).toLocaleString()}`) : '-'}
                                                        </p>
                                                        <p className="text-[10px] text-gray-600 font-mono mt-0.5">
                                                            ₩{trade.capital.toLocaleString()}
                                                        </p>
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
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                    </linearGradient>
                </defs>

                {[0, 0.25, 0.5, 0.75, 1].map(v => (
                    <line key={v} x1="0" y1={v * height} x2={width} y2={v * height}
                        stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                ))}

                <path d={areaPath} fill="url(#areaGradient)" className="animate-fade-in"
                    style={{ animationDelay: '0.5s', animationFillMode: 'both' }} />

                <path ref={pathRef} d={linePath} fill="none" stroke="#3b82f6" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"
                    style={{
                        strokeDasharray: pathLength,
                        strokeDashoffset: pathLength,
                        animation: `drawPath ${animationDuration}s cubic-bezier(0.4, 0, 0.2, 1) forwards`,
                    }} />

                {hoverIndex !== null && (
                    <>
                        <line x1={points[hoverIndex].x} y1="0" x2={points[hoverIndex].x} y2={height}
                            stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeDasharray="4 4" />
                        <circle cx={points[hoverIndex].x} cy={points[hoverIndex].y} r="5"
                            fill="#3b82f6" stroke="white" strokeWidth="2" />
                    </>
                )}
            </svg>

            <style jsx>{`
                @keyframes drawPath {
                    from { stroke-dashoffset: var(--path-length, 2000); }
                    to { stroke-dashoffset: 0; }
                }
                path { --path-length: ${pathLength}; }
            `}</style>

            {hoverIndex !== null && (
                <div
                    className="absolute z-10 p-3 rounded-xl bg-surface/95 border border-white/[0.08] backdrop-blur-md shadow-lg pointer-events-none"
                    style={{
                        left: `${(hoverIndex / (data.length - 1)) * 100}%`,
                        top: `${(points[hoverIndex].y / height) * 100}%`,
                        transform: `translate(${hoverIndex > data.length / 2 ? '-110%' : '10%'}, -50%)`
                    }}
                >
                    <p className="text-[10px] text-gray-500 mb-1">
                        {new Date(data[hoverIndex].time).toLocaleString()}
                    </p>
                    <p className="text-base font-bold text-white">
                        ₩{data[hoverIndex].value.toLocaleString()}
                    </p>
                    <p className={`text-xs font-medium flex items-center gap-1 ${data[hoverIndex].value >= data[0].value ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data[hoverIndex].value >= data[0].value ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {Math.abs(((data[hoverIndex].value - data[0].value) / data[0].value) * 100).toFixed(2)}%
                    </p>
                </div>
            )}
        </div>
    );
}
