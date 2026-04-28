'use client';
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { Play, TrendingUp, TrendingDown, Activity, Briefcase, History, Trash2, ArrowLeft, RefreshCw, Calendar } from 'lucide-react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select';
import PageContainer from '@/components/ui/PageContainer';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { useToast } from '@/components/ui/Toast';
import {
    runDualMomentumBacktest,
    getPortfolioHistory,
    getPortfolioHistoryDetail,
    deletePortfolioHistory,
    listPortfolioStrategies,
} from '@/lib/api/backtest';
import { formatKRW, getErrorMessage } from '@/lib/utils';
import type { PortfolioBacktestResult, PortfolioHistoryItem, PortfolioStrategyInfo } from '@/types/backtest';

const ASSET_LABELS: Record<string, string> = {
    '069500': 'KODEX 200 (국내)',
    '360750': 'TIGER 미국 S&P 500',
    '153130': 'KODEX 단기채권 (방어)',
};

const ASSET_COLORS: Record<string, string> = {
    '069500': '#3b82f6',
    '360750': '#22c55e',
    '153130': '#f59e0b',
};

function fmtPct(x: number): string {
    return `${x >= 0 ? '+' : ''}${(x * 100).toFixed(2)}%`;
}

export default function PortfolioBacktestPage() {
    const toast = useToast();

    const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
    const threeYearsAgo = useMemo(() => {
        const d = new Date();
        d.setFullYear(d.getFullYear() - 3);
        return d.toISOString().slice(0, 10);
    }, []);

    const [startDate, setStartDate] = useState(threeYearsAgo);
    const [endDate, setEndDate] = useState(today);
    const [initialCapital, setInitialCapital] = useState(10_000_000);
    const [commissionRate, setCommissionRate] = useState(0.001);
    const [strategyName, setStrategyName] = useState('dual_momentum_etf_v1');
    const [lookbackMonths, setLookbackMonths] = useState<number>(12);
    const [evaluationMode, setEvaluationMode] = useState<'preset' | 'sequential' | 'best_momentum'>('preset');
    const [rebalanceFreq, setRebalanceFreq] = useState<'monthly' | 'quarterly' | 'semiannual'>('monthly');
    const [strategies, setStrategies] = useState<PortfolioStrategyInfo[]>([]);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<PortfolioBacktestResult | null>(null);

    useEffect(() => {
        listPortfolioStrategies()
            .then(setStrategies)
            .catch(() => { /* 비차단 */ });
    }, []);

    // 탭/히스토리 상태
    const [activeTab, setActiveTab] = useState<'run' | 'history'>('run');
    const [historyList, setHistoryList] = useState<PortfolioHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [viewingHistoryId, setViewingHistoryId] = useState<number | null>(null);

    const fetchHistory = useCallback(async () => {
        setHistoryLoading(true);
        try {
            const data = await getPortfolioHistory(1, 50);
            setHistoryList(data);
        } catch (e) {
            toast.error(getErrorMessage(e, '히스토리 로드 실패'));
        } finally {
            setHistoryLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        if (activeTab === 'history' && !viewingHistoryId) {
            fetchHistory();
        }
    }, [activeTab, viewingHistoryId, fetchHistory]);

    const loadHistoryDetail = async (id: number) => {
        try {
            const detail = await getPortfolioHistoryDetail(id);
            if (detail.result_data) {
                setResult(detail.result_data);
                setViewingHistoryId(id);
            } else {
                toast.error('결과 데이터가 비어있습니다.');
            }
        } catch (e) {
            toast.error(getErrorMessage(e, '상세 로드 실패'));
        }
    };

    const handleDeleteHistory = async (id: number) => {
        if (!confirm('이 백테스트 기록을 삭제하시겠습니까?')) return;
        try {
            await deletePortfolioHistory(id);
            toast.success('삭제되었습니다.');
            fetchHistory();
        } catch (e) {
            toast.error(getErrorMessage(e, '삭제 실패'));
        }
    };

    const handleBackToList = () => {
        setViewingHistoryId(null);
        setResult(null);
    };

    // 동일 설정으로 재실행 — 히스토리 항목의 파라미터를 폼에 채우고 실행 탭으로 전환
    const handleRerun = (h: PortfolioHistoryItem) => {
        if (h.start_date) setStartDate(h.start_date);
        if (h.end_date) setEndDate(h.end_date);
        setInitialCapital(h.initial_capital);
        if (h.commission_rate != null) setCommissionRate(h.commission_rate);
        setStrategyName(h.strategy_name);
        if (h.custom_params?.lookback_months != null) setLookbackMonths(h.custom_params.lookback_months);
        const mode = h.custom_params?.evaluation_mode;
        setEvaluationMode(mode === 'sequential' || mode === 'best_momentum' ? mode : 'preset');
        const freq = h.custom_params?.rebalance_freq;
        setRebalanceFreq(freq === 'quarterly' || freq === 'semiannual' || freq === 'monthly' ? freq : 'monthly');
        setActiveTab('run');
        setViewingHistoryId(null);
        setResult(null);
        toast.success('설정이 채워졌습니다. 백테스트 실행을 눌러주세요.');
    };

    const handleRun = async () => {
        if (!startDate || !endDate) {
            toast.error('시작/종료일을 입력해주세요.');
            return;
        }
        if (new Date(endDate) <= new Date(startDate)) {
            toast.error('종료일은 시작일보다 뒤여야 합니다.');
            return;
        }
        if (initialCapital < 100_000) {
            toast.error('초기자본은 10만원 이상이어야 합니다.');
            return;
        }

        setLoading(true);
        setResult(null);
        try {
            const data = await runDualMomentumBacktest({
                strategy_name: strategyName,
                start_date: startDate,
                end_date: endDate,
                initial_capital: initialCapital,
                commission_rate: commissionRate,
                lookback_months: lookbackMonths,
                evaluation_mode: evaluationMode === 'preset' ? null : evaluationMode,
                rebalance_freq: rebalanceFreq,
            });
            setResult(data);
            toast.success('백테스트가 완료되었습니다.');
        } catch (e) {
            toast.error(getErrorMessage(e, '백테스트 실패'));
        } finally {
            setLoading(false);
        }
    };

    // 차트 데이터: equity + benchmarks (% 변화율 정규화, 시간축 합쳐서 단일 배열)
    const chartData = useMemo(() => {
        if (!result) return [];
        const map = new Map<string, Record<string, number>>();
        const first = result.equity_curve[0]?.value ?? result.initial_capital;
        result.equity_curve.forEach(p => {
            if (!map.has(p.time)) map.set(p.time, {});
            map.get(p.time)!.equity = ((p.value / first) - 1) * 100;
        });
        if (result.benchmarks) {
            for (const [asset, points] of Object.entries(result.benchmarks)) {
                const bhFirst = points[0]?.value ?? result.initial_capital;
                points.forEach(p => {
                    if (!map.has(p.time)) map.set(p.time, {});
                    map.get(p.time)![`bh_${asset}`] = ((p.value / bhFirst) - 1) * 100;
                });
            }
        }
        return Array.from(map.entries())
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([time, vals]) => ({ time, _zero: 0, ...vals }));
    }, [result]);

    // 차트 라인 토글
    const [chartVisible, setChartVisible] = useState<Record<string, boolean>>({ equity: true });
    useEffect(() => {
        if (!result) return;
        setChartVisible(prev => {
            const next: Record<string, boolean> = { ...prev, equity: true };
            for (const a of Object.keys(result.benchmarks || {})) {
                const k = `bh_${a}`;
                if (!(k in next)) next[k] = true;
            }
            return next;
        });
    }, [result]);

    // 자산 회전 타임라인 — rebalance_log를 인접 동일 자산끼리 묶음
    const timelineSegments = useMemo(() => {
        if (!result || result.rebalance_log.length === 0) return [];
        const log = result.rebalance_log;
        const segs: { asset: string | null; start: string; end: string }[] = [];
        let cur = { asset: log[0].selected_asset, start: log[0].date, end: log[0].date };
        for (let i = 1; i < log.length; i++) {
            const r = log[i];
            if (r.selected_asset === cur.asset) {
                cur.end = r.date;
            } else {
                segs.push({ ...cur });
                cur = { asset: r.selected_asset, start: r.date, end: r.date };
            }
        }
        segs.push(cur);
        // 비율 계산용 — 첫 시작 → 마지막 끝
        const first = new Date(segs[0].start).getTime();
        const last = new Date(segs[segs.length - 1].end).getTime();
        const span = Math.max(last - first, 1);
        return segs.map(s => ({
            ...s,
            offsetPct: ((new Date(s.start).getTime() - first) / span) * 100,
            widthPct: Math.max(((new Date(s.end).getTime() - new Date(s.start).getTime()) / span) * 100, 1),
        }));
    }, [result]);

    // 연도별 수익률 — equity_curve의 각 연도 마지막 시점 값으로 계산
    // 첫 해는 시작값 대비, 이후 해는 직전 해 마지막 대비
    const annualReturns = useMemo(() => {
        if (!result || result.equity_curve.length === 0) return [];
        const byYear: Map<number, number> = new Map();
        for (const p of result.equity_curve) {
            const y = new Date(p.time).getUTCFullYear();
            byYear.set(y, p.value); // 같은 해 마지막 포인트가 자동으로 덮어씀 (정렬 가정)
        }
        const years = Array.from(byYear.keys()).sort((a, b) => a - b);
        const rows: { year: number; ret: number; endValue: number }[] = [];
        let prev = result.initial_capital;
        for (const y of years) {
            const v = byYear.get(y)!;
            const ret = prev > 0 ? (v - prev) / prev : 0;
            rows.push({ year: y, ret, endValue: v });
            prev = v;
        }
        return rows;
    }, [result]);

    const totalDays = useMemo(() => {
        if (!result) return 0;
        return Object.values(result.holding_periods).reduce((a, b) => a + b, 0);
    }, [result]);

    const evalModeLabel = (m?: string | null) => {
        if (!m) return '프리셋';
        if (m === 'sequential') return 'Sequential';
        if (m === 'best_momentum') return 'Best';
        return m;
    };
    const freqLabel = (f?: string | null) => {
        if (!f || f === 'monthly') return '월말';
        if (f === 'quarterly') return '분기말';
        if (f === 'semiannual') return '반기말';
        return f;
    };

    return (
        <PageContainer>
            <div className="mb-6 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                    <Briefcase className="w-5 h-5 text-primary" />
                </div>
                <div className="flex-1">
                    <h1 className="text-xl font-bold text-th-text">포트폴리오 백테스트</h1>
                    <p className="text-xs text-th-text-muted">한국 ETF 듀얼 모멘텀 전략 — 월말 리밸런싱</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-6 border-b border-th-border-light">
                <button
                    onClick={() => { setActiveTab('run'); setViewingHistoryId(null); }}
                    className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                        activeTab === 'run'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-th-text-muted hover:text-th-text'
                    }`}
                >
                    <Play className="w-4 h-4 inline mr-1.5" />실행
                </button>
                <button
                    onClick={() => { setActiveTab('history'); setViewingHistoryId(null); setResult(null); }}
                    className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors ${
                        activeTab === 'history'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-th-text-muted hover:text-th-text'
                    }`}
                >
                    <History className="w-4 h-4 inline mr-1.5" />기록
                </button>
            </div>

            {/* History list view */}
            {activeTab === 'history' && !viewingHistoryId && (
                <Card>
                    <CardHeader>
                        <CardTitle>실행 기록</CardTitle>
                        <CardDescription>저장된 포트폴리오 백테스트 결과 ({historyList.length}건)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {historyLoading ? (
                            <div className="flex justify-center py-8"><LoadingSpinner /></div>
                        ) : historyList.length === 0 ? (
                            <div className="text-center py-12 text-sm text-th-text-muted">
                                저장된 기록이 없습니다. '실행' 탭에서 백테스트를 진행해보세요.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {historyList.map(h => {
                                    const ret = (h.final_capital !== null && h.initial_capital > 0)
                                        ? (h.final_capital - h.initial_capital) / h.initial_capital
                                        : null;
                                    return (
                                        <button
                                            key={h.id}
                                            onClick={() => loadHistoryDetail(h.id)}
                                            className="w-full text-left p-4 rounded-xl bg-white/[0.02] border border-th-border-light hover:bg-white/[0.04] hover:border-th-border transition-colors group"
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-sm font-semibold text-th-text">
                                                            {h.title || h.strategy_name}
                                                        </span>
                                                        <span className="text-[10px] sm:text-xs text-th-text-muted">
                                                            {h.assets.join(', ')}
                                                        </span>
                                                    </div>
                                                    <div className="text-[10px] sm:text-xs text-th-text-muted mb-1.5">
                                                        {h.start_date} ~ {h.end_date} • 거래 {h.total_trades || 0}건 • {new Date(h.created_at).toLocaleString('ko-KR')}
                                                    </div>
                                                    {/* 메타 배지: lookback / mode / freq */}
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {h.custom_params?.lookback_months != null && (
                                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                                                {h.custom_params.lookback_months}M
                                                            </span>
                                                        )}
                                                        {h.custom_params?.evaluation_mode && (
                                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                                                                {evalModeLabel(h.custom_params.evaluation_mode)}
                                                            </span>
                                                        )}
                                                        {h.custom_params?.rebalance_freq && (
                                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                                                {freqLabel(h.custom_params.rebalance_freq)}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2 shrink-0">
                                                    {ret !== null && (
                                                        <span className={`text-sm font-bold ${ret >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {fmtPct(ret)}
                                                        </span>
                                                    )}
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleRerun(h); }}
                                                        className="p-1.5 rounded-lg text-th-text-muted hover:text-primary hover:bg-primary/10 transition-colors"
                                                        aria-label="동일 설정으로 재실행"
                                                        title="동일 설정으로 재실행"
                                                    >
                                                        <RefreshCw className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleDeleteHistory(h.id); }}
                                                        className="p-1.5 rounded-lg text-th-text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                                        aria-label="삭제"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* History detail view */}
            {activeTab === 'history' && viewingHistoryId && (
                <div className="mb-4">
                    <Button variant="ghost" size="sm" onClick={handleBackToList}>
                        <ArrowLeft className="w-4 h-4" /> 목록으로
                    </Button>
                </div>
            )}

            {/* Input panel — only on run tab */}
            {activeTab === 'run' && (
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle>설정</CardTitle>
                    <CardDescription>
                        한국 ETF 듀얼 모멘텀 — 전략/lookback/리밸런스 주기 선택 가능
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {/* Strategy selector */}
                    <div className="mb-4">
                        <label className="text-xs text-th-text-muted font-medium mb-1.5 block">전략</label>
                        <Select value={strategyName} onValueChange={setStrategyName} disabled={loading}>
                            <SelectTrigger>
                                <SelectValue placeholder="전략을 선택하세요" />
                            </SelectTrigger>
                            <SelectContent>
                                {strategies.length === 0 && (
                                    <SelectItem value="dual_momentum_etf_v1">듀얼 모멘텀 v1 (KR+US)</SelectItem>
                                )}
                                {strategies.map(s => (
                                    <SelectItem key={s.name} value={s.name}>{s.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {strategies.find(s => s.name === strategyName)?.description && (
                            <p className="mt-1.5 text-[10px] sm:text-xs text-th-text-muted">
                                {strategies.find(s => s.name === strategyName)!.description}
                            </p>
                        )}
                    </div>

                    {/* Strategy params */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                        <div>
                            <label className="text-xs text-th-text-muted font-medium mb-1.5 block">Lookback 기간</label>
                            <Select
                                value={String(lookbackMonths)}
                                onValueChange={(v) => setLookbackMonths(Number(v))}
                                disabled={loading}
                            >
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="3">3개월</SelectItem>
                                    <SelectItem value="6">6개월</SelectItem>
                                    <SelectItem value="9">9개월</SelectItem>
                                    <SelectItem value="12">12개월 (기본)</SelectItem>
                                    <SelectItem value="18">18개월</SelectItem>
                                    <SelectItem value="24">24개월</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="text-xs text-th-text-muted font-medium mb-1.5 block">평가 모드</label>
                            <Select
                                value={evaluationMode}
                                onValueChange={(v) => setEvaluationMode(v as typeof evaluationMode)}
                                disabled={loading}
                            >
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="preset">프리셋 그대로</SelectItem>
                                    <SelectItem value="sequential">Sequential (순차)</SelectItem>
                                    <SelectItem value="best_momentum">Best momentum (Antonacci)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <label className="text-xs text-th-text-muted font-medium mb-1.5 block">리밸런스 주기</label>
                            <Select
                                value={rebalanceFreq}
                                onValueChange={(v) => setRebalanceFreq(v as typeof rebalanceFreq)}
                                disabled={loading}
                            >
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="monthly">월말 (기본)</SelectItem>
                                    <SelectItem value="quarterly">분기말</SelectItem>
                                    <SelectItem value="semiannual">반기말</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Input
                            label="시작일"
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            disabled={loading}
                        />
                        <Input
                            label="종료일"
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            disabled={loading}
                        />
                        <Input
                            label="초기자본 (KRW)"
                            type="number"
                            min={100000}
                            step={100000}
                            value={initialCapital}
                            onChange={(e) => setInitialCapital(Number(e.target.value))}
                            disabled={loading}
                        />
                        <Input
                            label="수수료율 (예: 0.001 = 0.1%)"
                            type="number"
                            min={0}
                            max={0.01}
                            step={0.0001}
                            value={commissionRate}
                            onChange={(e) => setCommissionRate(Number(e.target.value))}
                            disabled={loading}
                        />
                    </div>
                    <div className="mt-5 flex justify-end">
                        <Button onClick={handleRun} disabled={loading} size="md">
                            {loading ? (
                                <>
                                    <LoadingSpinner size="sm" /> 실행 중...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4" /> 백테스트 실행
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>
            )}

            {/* Result */}
            {result && (
                <>
                    {/* Metrics summary */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                        <MetricCard
                            label="총 수익률"
                            value={fmtPct(result.total_return)}
                            positive={result.total_return >= 0}
                            icon={result.total_return >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                        />
                        <MetricCard label="CAGR" value={fmtPct(result.cagr)} positive={result.cagr >= 0} />
                        <MetricCard label="최대 낙폭 (MDD)" value={fmtPct(result.max_drawdown)} positive={false} />
                        <MetricCard label="Sharpe" value={result.sharpe.toFixed(2)} />
                    </div>

                    {/* Equity chart with benchmarks */}
                    <Card className="mb-6">
                        <CardHeader>
                            <CardTitle>자산 추이 + 벤치마크 비교</CardTitle>
                            <CardDescription>
                                초기자본 {formatKRW(result.initial_capital)} → 최종 {formatKRW(result.final_capital)}
                                {' • '}리밸런스 {result.total_rebalances}회
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {/* Toggle legend */}
                            <div className="flex flex-wrap gap-2 mb-3">
                                <button
                                    type="button"
                                    onClick={() => { /* equity always on */ }}
                                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] sm:text-xs font-medium bg-white/[0.06] text-th-text cursor-default"
                                >
                                    <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: '#3b82f6' }} />
                                    전략 (DM)
                                </button>
                                {Object.keys(result.benchmarks || {}).map(asset => {
                                    const k = `bh_${asset}`;
                                    const visible = chartVisible[k];
                                    return (
                                        <button
                                            type="button"
                                            key={asset}
                                            onClick={() => setChartVisible(p => ({ ...p, [k]: !p[k] }))}
                                            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] sm:text-xs font-medium transition-all ${visible ? 'bg-white/[0.06] text-th-text' : 'bg-white/[0.02] text-th-text-muted line-through'}`}
                                        >
                                            <span
                                                className="w-3 inline-block"
                                                style={{
                                                    height: '2px',
                                                    backgroundImage: `repeating-linear-gradient(90deg, ${ASSET_COLORS[asset] || '#9ca3af'} 0, ${ASSET_COLORS[asset] || '#9ca3af'} 4px, transparent 4px, transparent 7px)`,
                                                }}
                                            />
                                            BH {asset} {ASSET_LABELS[asset] && <span className="text-th-text-muted">({ASSET_LABELS[asset].split(' ')[0]})</span>}
                                        </button>
                                    );
                                })}
                            </div>

                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                                    <XAxis dataKey="time" stroke="#6b7280" fontSize={11} tickLine={false} interval="preserveStartEnd" />
                                    <YAxis
                                        stroke="#6b7280"
                                        fontSize={11}
                                        tickLine={false}
                                        tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`}
                                        domain={['auto', 'auto']}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            borderRadius: '12px',
                                            fontSize: '12px',
                                            padding: '10px 14px',
                                        }}
                                        formatter={(value, name) => {
                                            if (name === '_zero' || value === undefined || value === null) return [null, null];
                                            const v = Number(value);
                                            const label = name === 'equity'
                                                ? '전략 (DM)'
                                                : String(name).startsWith('bh_')
                                                    ? `BH ${String(name).slice(3)}`
                                                    : String(name);
                                            return [`${v > 0 ? '+' : ''}${v.toFixed(2)}%`, label];
                                        }}
                                        labelFormatter={(label) => label}
                                    />
                                    {/* Zero baseline */}
                                    <Line type="monotone" dataKey="_zero" stroke="rgba(255,255,255,0.1)" strokeWidth={1} dot={false} strokeDasharray="4 4" isAnimationActive={false} />
                                    {/* Strategy equity */}
                                    <Line
                                        type="monotone"
                                        dataKey="equity"
                                        stroke="#3b82f6"
                                        strokeWidth={2.5}
                                        dot={false}
                                        activeDot={{ r: 4, stroke: '#3b82f6', strokeWidth: 2, fill: '#111827' }}
                                        connectNulls
                                    />
                                    {/* Benchmarks */}
                                    {Object.keys(result.benchmarks || {}).map(asset => (
                                        chartVisible[`bh_${asset}`] && (
                                            <Line
                                                key={asset}
                                                type="monotone"
                                                dataKey={`bh_${asset}`}
                                                stroke={ASSET_COLORS[asset] || '#9ca3af'}
                                                strokeWidth={1.5}
                                                strokeDasharray="6 3"
                                                dot={false}
                                                activeDot={{ r: 3 }}
                                                connectNulls
                                            />
                                        )
                                    ))}
                                </LineChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>

                    {/* Asset rotation timeline */}
                    {timelineSegments.length > 0 && (
                        <Card className="mb-6">
                            <CardHeader>
                                <CardTitle>자산 회전 타임라인</CardTitle>
                                <CardDescription>
                                    리밸런스 시점에 선택된 자산 — 색 막대 길이가 해당 자산 보유 기간
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="relative h-10 mb-3 rounded-lg bg-white/[0.02] overflow-hidden">
                                    {timelineSegments.map((seg, i) => (
                                        <div
                                            key={i}
                                            title={`${seg.asset || '없음'} • ${seg.start} ~ ${seg.end}`}
                                            className="absolute top-0 bottom-0 transition-all hover:brightness-125"
                                            style={{
                                                left: `${seg.offsetPct}%`,
                                                width: `${seg.widthPct}%`,
                                                backgroundColor: seg.asset ? (ASSET_COLORS[seg.asset] || '#6b7280') : '#374151',
                                                opacity: 0.85,
                                            }}
                                        />
                                    ))}
                                </div>
                                <div className="flex justify-between text-[10px] sm:text-xs text-th-text-muted">
                                    <span>{timelineSegments[0]?.start}</span>
                                    <span>{timelineSegments[timelineSegments.length - 1]?.end}</span>
                                </div>
                                <div className="mt-3 flex flex-wrap gap-3 text-[10px] sm:text-xs">
                                    {result.assets.map(a => (
                                        <span key={a} className="flex items-center gap-1.5 text-th-text-secondary">
                                            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: ASSET_COLORS[a] || '#6b7280' }} />
                                            {a} {ASSET_LABELS[a] && <span className="text-th-text-muted">— {ASSET_LABELS[a]}</span>}
                                        </span>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Annual returns table */}
                    {annualReturns.length > 0 && (
                        <Card className="mb-6">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Calendar className="w-4 h-4 text-primary" />
                                    연도별 수익률
                                </CardTitle>
                                <CardDescription>
                                    각 연도 마지막 시점의 자산 가치 변화
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs">
                                        <thead>
                                            <tr className="text-th-text-muted border-b border-th-border-light">
                                                <th className="text-left py-2 px-3">연도</th>
                                                <th className="text-right py-2 px-3">수익률</th>
                                                <th className="text-right py-2 px-3">연말 자산</th>
                                                <th className="text-left py-2 px-3 hidden sm:table-cell w-1/2">시각화</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {annualReturns.map(r => {
                                                const positive = r.ret >= 0;
                                                const barWidth = Math.min(Math.abs(r.ret) * 100 * 2, 100); // 50% 수익 = 100% bar
                                                return (
                                                    <tr key={r.year} className="border-b border-th-border-light/50 hover:bg-white/[0.02]">
                                                        <td className="py-2 px-3 font-semibold text-th-text">{r.year}</td>
                                                        <td className={`py-2 px-3 text-right font-bold ${positive ? 'text-green-400' : 'text-red-400'}`}>
                                                            {fmtPct(r.ret)}
                                                        </td>
                                                        <td className="py-2 px-3 text-right text-th-text-secondary">
                                                            {Math.round(r.endValue).toLocaleString()}
                                                        </td>
                                                        <td className="py-2 px-3 hidden sm:table-cell">
                                                            <div className="relative h-3 bg-white/[0.03] rounded">
                                                                <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/[0.1]" />
                                                                <div
                                                                    className={`absolute top-0 bottom-0 ${positive ? 'bg-green-400/40 left-1/2' : 'bg-red-400/40'}`}
                                                                    style={positive
                                                                        ? { width: `${barWidth / 2}%` }
                                                                        : { width: `${barWidth / 2}%`, right: '50%' }
                                                                    }
                                                                />
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Asset distribution */}
                    <Card className="mb-6">
                        <CardHeader>
                            <CardTitle>자산 보유 분포</CardTitle>
                            <CardDescription>총 보유 일수 {totalDays}일 기준</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {result.assets.map(asset => {
                                    const days = result.holding_periods[asset] || 0;
                                    const pct = totalDays > 0 ? (days / totalDays) * 100 : 0;
                                    return (
                                        <div key={asset}>
                                            <div className="flex justify-between text-xs mb-1">
                                                <span className="text-th-text">
                                                    <span
                                                        className="inline-block w-2 h-2 rounded-full mr-2"
                                                        style={{ backgroundColor: ASSET_COLORS[asset] || '#6b7280' }}
                                                    />
                                                    {asset} <span className="text-th-text-muted">— {ASSET_LABELS[asset] || ''}</span>
                                                </span>
                                                <span className="text-th-text-secondary">{days}일 ({pct.toFixed(1)}%)</span>
                                            </div>
                                            <div className="h-2 rounded-full bg-white/[0.04] overflow-hidden">
                                                <div
                                                    className="h-full transition-all duration-500"
                                                    style={{
                                                        width: `${pct}%`,
                                                        backgroundColor: ASSET_COLORS[asset] || '#6b7280',
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Trades table */}
                    <Card>
                        <CardHeader>
                            <CardTitle>거래 내역 ({result.trades.length}건)</CardTitle>
                            <CardDescription>리밸런스 시점에 발생한 매수/매도</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead>
                                        <tr className="text-th-text-muted border-b border-th-border-light">
                                            <th className="text-left py-2 px-3">날짜</th>
                                            <th className="text-left py-2 px-3">구분</th>
                                            <th className="text-left py-2 px-3">자산</th>
                                            <th className="text-right py-2 px-3">가격</th>
                                            <th className="text-right py-2 px-3">수량</th>
                                            <th className="text-right py-2 px-3">금액</th>
                                            <th className="text-right py-2 px-3">수수료</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.trades.map((t, i) => (
                                            <tr key={i} className="border-b border-th-border-light/50 hover:bg-white/[0.02]">
                                                <td className="py-2 px-3 text-th-text-secondary">{t.date}</td>
                                                <td className="py-2 px-3">
                                                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] sm:text-xs font-semibold ${t.side === 'BUY' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                                                        {t.side}
                                                    </span>
                                                </td>
                                                <td className="py-2 px-3 text-th-text">{t.asset}</td>
                                                <td className="py-2 px-3 text-right text-th-text-secondary">{t.price.toLocaleString()}</td>
                                                <td className="py-2 px-3 text-right text-th-text-secondary">{t.units.toFixed(4)}</td>
                                                <td className="py-2 px-3 text-right text-th-text-secondary">
                                                    {Math.round(t.cost ?? t.proceeds ?? 0).toLocaleString()}
                                                </td>
                                                <td className="py-2 px-3 text-right text-th-text-muted">{Math.round(t.fee).toLocaleString()}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                {result.trades.length === 0 && (
                                    <div className="text-center py-8 text-sm text-th-text-muted">
                                        거래가 발생하지 않았습니다.
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            {activeTab === 'run' && !result && !loading && (
                <Card>
                    <CardContent>
                        <div className="text-center py-12 text-th-text-muted">
                            <Activity className="w-10 h-10 mx-auto mb-3 opacity-40" />
                            <p className="text-sm">설정을 입력하고 백테스트를 실행해주세요.</p>
                        </div>
                    </CardContent>
                </Card>
            )}
        </PageContainer>
    );
}

interface MetricCardProps {
    label: string;
    value: string;
    positive?: boolean;
    icon?: React.ReactNode;
}

function MetricCard({ label, value, positive, icon }: MetricCardProps) {
    const colorClass = positive === undefined
        ? 'text-th-text'
        : positive
            ? 'text-green-400'
            : 'text-red-400';
    return (
        <Card>
            <div className="p-4">
                <div className="flex items-center gap-1.5 text-[10px] sm:text-xs text-th-text-muted mb-1.5">
                    {icon}
                    <span>{label}</span>
                </div>
                <div className={`text-xl font-bold ${colorClass}`}>{value}</div>
            </div>
        </Card>
    );
}
