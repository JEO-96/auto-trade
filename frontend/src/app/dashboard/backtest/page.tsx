'use client';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Activity, CheckCircle2, TrendingUp, TrendingDown, Settings, History, Share2, X, Trash2 } from 'lucide-react';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import Badge from '@/components/ui/Badge';
import PageContainer from '@/components/ui/PageContainer';
import { SYMBOLS, BACKTEST_POLL_INTERVAL_MS } from '@/lib/constants';
import { runPortfolioBacktest, getBacktestStatus, getBacktestHistory, getBacktestHistoryDetail, shareBacktestToCommunity, deleteBacktestHistory } from '@/lib/api/backtest';
import { getErrorMessage } from '@/lib/utils';
import type { BacktestResult, BacktestTrade, EquityCurvePoint, BacktestHistoryItem } from '@/types/backtest';

export default function BacktestPage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<BacktestResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // 기록 탭 상태
    const [activeTab, setActiveTab] = useState<'run' | 'history'>('run');
    const [historyList, setHistoryList] = useState<BacktestHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [viewingHistoryId, setViewingHistoryId] = useState<number | null>(null);

    // 공유 모달 상태
    const [shareModal, setShareModal] = useState<{ historyId: number } | null>(null);
    const [shareTitle, setShareTitle] = useState('');
    const [shareContent, setShareContent] = useState('');
    const [sharing, setSharing] = useState(false);
    const [shareSuccess, setShareSuccess] = useState(false);

    const fetchHistory = useCallback(async () => {
        setHistoryLoading(true);
        try {
            const data = await getBacktestHistory(1, 50);
            setHistoryList(data);
        } catch (err) {
            console.error('백테스트 기록 로드 실패', err);
        } finally {
            setHistoryLoading(false);
        }
    }, []);

    const loadHistoryDetail = async (id: number) => {
        try {
            const detail = await getBacktestHistoryDetail(id);
            if (detail.result_data) {
                setResult(detail.result_data);
                setViewingHistoryId(id);
                setActiveTab('run');
            }
        } catch (err) {
            console.error('백테스트 상세 로드 실패', err);
        }
    };

    const handleShare = async () => {
        if (!shareModal || !shareTitle.trim()) return;
        setSharing(true);
        try {
            await shareBacktestToCommunity(
                shareModal.historyId,
                shareTitle.trim(),
                shareContent.trim() || undefined,
            );
            setShareSuccess(true);
            setTimeout(() => {
                setShareModal(null);
                setShareTitle('');
                setShareContent('');
                setShareSuccess(false);
            }, 1500);
        } catch (err) {
            console.error('공유 실패', err);
        } finally {
            setSharing(false);
        }
    };

    useEffect(() => {
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, []);

    const handleDeleteHistory = async (id: number) => {
        if (!confirm('이 백테스트 기록을 삭제하시겠습니까?')) return;
        try {
            await deleteBacktestHistory(id);
            setHistoryList(prev => prev.filter(h => h.id !== id));
        } catch (err) {
            console.error('백테스트 기록 삭제 실패', err);
        }
    };

    useEffect(() => {
        if (activeTab === 'history') fetchHistory();
    }, [activeTab, fetchHistory]);

    const [form, setForm] = useState(() => {
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - 3);
        return {
            symbols: ['BTC/KRW'],
            timeframe: '1h',
            strategy_name: 'james_pro_elite',
            initial_capital: 1000000,
            start_date: start.toISOString().split('T')[0],
            end_date: end.toISOString().split('T')[0],
            commission_rate_pct: 0.05,
            period_preset: '3m' as string,
        };
    });

    const toggleSymbol = (symbol: string) => {
        setForm(prev => {
            const symbols = prev.symbols.includes(symbol)
                ? prev.symbols.filter(s => s !== symbol)
                : [...prev.symbols, symbol];
            return { ...prev, symbols: symbols.length > 0 ? symbols : prev.symbols };
        });
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setForm({ ...form, [name]: value, period_preset: '' });
    };

    const setPeriodPreset = (key: string, months: number) => {
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - months);
        setForm({
            ...form,
            start_date: start.toISOString().split('T')[0],
            end_date: end.toISOString().split('T')[0],
            period_preset: key,
        });
    };

    const pollStatus = async (taskId: string) => {
        intervalRef.current = setInterval(async () => {
            try {
                const data = await getBacktestStatus(taskId);

                setProgress(data.progress);
                setProgressMessage(data.message);

                if (data.status === 'completed') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setResult(data.result ?? null);
                    setLoading(false);
                } else if (data.status === 'failed') {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    setError(data.message || '백테스트 중 오류가 발생했습니다.');
                    setLoading(false);
                }
            } catch {
                if (intervalRef.current) clearInterval(intervalRef.current);
                setError('상태 확인 중 오류가 발생했습니다.');
                setLoading(false);
            }
        }, BACKTEST_POLL_INTERVAL_MS);
    };

    const runBacktest = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);
        setProgress(0);
        setProgressMessage('백테스트 작업을 시작합니다...');

        try {
            const data = await runPortfolioBacktest({
                symbols: form.symbols,
                timeframe: form.timeframe,
                strategy_name: form.strategy_name,
                limit: null,
                start_date: form.start_date || null,
                end_date: form.end_date || null,
                initial_capital: Number(form.initial_capital),
                commission_rate: form.commission_rate_pct / 100,
            });

            if (data.status === 'running' && data.task_id) {
                pollStatus(data.task_id);
            } else if (data.status === 'success') {
                setResult(data as unknown as BacktestResult);
                setLoading(false);
            } else {
                setError(data.message || '백테스트 중 오류가 발생했습니다.');
                setLoading(false);
            }
        } catch (err: unknown) {
            setError(getErrorMessage(err, '서버와의 통신에 실패했습니다.'));
            setLoading(false);
        }
    };

    return (
        <PageContainer>
            <header className="mb-6">
                <h1 className="text-2xl font-bold mb-1 text-white">전략 백테스팅</h1>
                <p className="text-sm text-gray-500 max-w-xl mb-4">
                    모멘텀 돌파 알고리즘의 과거 성과를 분석하고 포트폴리오 시뮬레이션으로 검증하세요.
                </p>
                <div className="flex gap-1.5 bg-white/[0.02] p-1 rounded-xl border border-white/[0.04] w-fit">
                    <button
                        onClick={() => setActiveTab('run')}
                        className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${activeTab === 'run' ? 'bg-primary/10 text-primary' : 'text-gray-500 hover:text-white'}`}
                    >
                        <Play className="w-3.5 h-3.5" /> 실행
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-all ${activeTab === 'history' ? 'bg-primary/10 text-primary' : 'text-gray-500 hover:text-white'}`}
                    >
                        <History className="w-3.5 h-3.5" /> 기록
                    </button>
                </div>
            </header>

            {/* 공유 모달 */}
            {shareModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="glass-panel rounded-2xl p-6 w-full max-w-md mx-4">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold text-white">커뮤니티에 공유</h3>
                            <button onClick={() => setShareModal(null)} className="text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
                        </div>
                        {shareSuccess ? (
                            <div className="text-center py-8">
                                <CheckCircle2 className="w-10 h-10 text-secondary mx-auto mb-3" />
                                <p className="text-sm text-secondary font-semibold">커뮤니티에 공유되었습니다!</p>
                            </div>
                        ) : (
                            <>
                                <input
                                    value={shareTitle}
                                    onChange={(e) => setShareTitle(e.target.value)}
                                    placeholder="제목을 입력하세요"
                                    maxLength={100}
                                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 mb-3 focus:border-primary/30 transition-colors"
                                />
                                <textarea
                                    value={shareContent}
                                    onChange={(e) => setShareContent(e.target.value)}
                                    placeholder="소감이나 분석 내용을 작성하세요 (선택)"
                                    rows={3}
                                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 mb-4 resize-none focus:border-primary/30 transition-colors"
                                />
                                <div className="flex gap-2">
                                    <Button onClick={handleShare} loading={sharing} disabled={!shareTitle.trim()} size="sm">
                                        <Share2 className="w-3.5 h-3.5" /> 공유하기
                                    </Button>
                                    <Button variant="ghost" size="sm" onClick={() => setShareModal(null)}>취소</Button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* 기록 탭 */}
            {activeTab === 'history' && (
                <div className="glass-panel rounded-2xl p-6">
                    <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                        <History className="w-5 h-5 text-primary" />
                        백테스트 기록
                    </h3>
                    {historyLoading ? (
                        <div className="flex justify-center py-12"><LoadingSpinner message="기록 불러오는 중..." /></div>
                    ) : historyList.length === 0 ? (
                        <EmptyState icon={<History className="w-12 h-12" />} title="백테스트 기록이 없습니다" description="백테스트를 실행하면 자동으로 기록됩니다." />
                    ) : (
                        <div className="space-y-2">
                            {historyList.map((h) => {
                                const pnlPct = h.final_capital && h.initial_capital
                                    ? ((h.final_capital - h.initial_capital) / h.initial_capital * 100)
                                    : null;
                                const isProfit = pnlPct !== null && pnlPct >= 0;
                                return (
                                    <div key={h.id} className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors group">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Badge variant={h.status === 'completed' ? 'success' : h.status === 'failed' ? 'danger' : 'warning'}>
                                                    {h.status === 'completed' ? '완료' : h.status === 'failed' ? '실패' : '진행중'}
                                                </Badge>
                                                <span className="text-xs text-gray-400 font-medium">{h.strategy_name}</span>
                                            </div>
                                            <div className="flex items-center gap-3 text-[11px] text-gray-500">
                                                <span>{(h.symbols || []).join(', ')}</span>
                                                <span>{h.timeframe}</span>
                                                <span>₩{h.initial_capital.toLocaleString()}</span>
                                                <span>{new Date(h.created_at).toLocaleDateString('ko-KR')}</span>
                                            </div>
                                        </div>
                                        {pnlPct !== null && (
                                            <div className="text-right shrink-0">
                                                <p className={`text-sm font-bold ${isProfit ? 'text-secondary' : 'text-red-400'}`}>
                                                    {isProfit ? '+' : ''}{pnlPct.toFixed(2)}%
                                                </p>
                                                <p className="text-[10px] text-gray-500">{h.total_trades}회 거래</p>
                                            </div>
                                        )}
                                        <div className="flex items-center gap-1.5 shrink-0">
                                            {h.status === 'completed' && (
                                                <>
                                                    <button
                                                        onClick={() => loadHistoryDetail(h.id)}
                                                        className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-gray-400 hover:text-white hover:bg-white/[0.04] transition-colors"
                                                    >
                                                        상세보기
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            setShareModal({ historyId: h.id });
                                                            setShareTitle(`${h.strategy_name} 백테스트 결과 (${(h.symbols || []).join(', ')})`);
                                                        }}
                                                        className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-primary hover:bg-primary/10 transition-colors flex items-center gap-1"
                                                    >
                                                        <Share2 className="w-3 h-3" /> 공유
                                                    </button>
                                                </>
                                            )}
                                            <button
                                                onClick={() => handleDeleteHistory(h.id)}
                                                className="px-2 py-1.5 rounded-lg text-[11px] text-gray-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                                                title="삭제"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {activeTab === 'run' && <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
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
                                    {SYMBOLS.map(s => (
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
                                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm font-medium text-white appearance-none cursor-pointer focus:border-primary/30 transition-colors [&>option]:bg-[#1e293b] [&>option]:text-white"
                                >
                                    <option value="james_pro_elite">모멘텀 PRO (초고수익형)</option>
                                    <option value="james_pro_stable">모멘텀 PRO (안정형)</option>
                                    <option value="james_pro_aggressive">모멘텀 PRO (공격형)</option>
                                    <option value="james_basic">모멘텀 돌파 (기본)</option>
                                    <option value="steady_compounder">스테디 복리 (주간 안정형)</option>
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

                            {/* 테스트 기간 */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">테스트 기간</label>
                                <div className="grid grid-cols-3 gap-1.5 mb-3">
                                    {[
                                        { key: '1m', label: '1개월', months: 1 },
                                        { key: '3m', label: '3개월', months: 3 },
                                        { key: '6m', label: '6개월', months: 6 },
                                        { key: '1y', label: '1년', months: 12 },
                                        { key: '2y', label: '2년', months: 24 },
                                        { key: '3y', label: '3년', months: 36 },
                                    ].map(preset => (
                                        <button
                                            key={preset.key}
                                            type="button"
                                            onClick={() => setPeriodPreset(preset.key, preset.months)}
                                            className={`py-2 text-xs font-semibold rounded-lg transition-all border ${
                                                form.period_preset === preset.key
                                                    ? 'bg-primary/10 border-primary/30 text-primary'
                                                    : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:text-gray-300 hover:border-white/10'
                                            }`}
                                        >
                                            {preset.label}
                                        </button>
                                    ))}
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <label className="text-[10px] text-gray-500 font-medium mb-1 block">시작일</label>
                                        <input
                                            type="date"
                                            name="start_date"
                                            value={form.start_date}
                                            onChange={handleChange}
                                            className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2.5 text-xs text-white focus:border-primary/30 transition-colors [color-scheme:dark]"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-[10px] text-gray-500 font-medium mb-1 block">종료일</label>
                                        <input
                                            type="date"
                                            name="end_date"
                                            value={form.end_date}
                                            onChange={handleChange}
                                            className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2.5 text-xs text-white focus:border-primary/30 transition-colors [color-scheme:dark]"
                                        />
                                    </div>
                                </div>
                                {form.start_date && form.end_date && (
                                    <p className="text-[10px] text-gray-500 text-center mt-2">
                                        {form.start_date} ~ {form.end_date}
                                        <span className="ml-1.5 text-primary font-semibold">
                                            ({Math.ceil((new Date(form.end_date).getTime() - new Date(form.start_date).getTime()) / 86400000)}일)
                                        </span>
                                    </p>
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

                            {/* Commission Rate */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">수수료율 (%)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    max="10"
                                    value={form.commission_rate_pct}
                                    onChange={(e) => setForm({ ...form, commission_rate_pct: parseFloat(e.target.value) || 0 })}
                                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm font-medium text-white focus:border-primary/30 transition-colors font-mono"
                                    placeholder="0.05"
                                />
                                <p className="text-[10px] text-gray-600 mt-1.5">
                                    예: 0.05 = 0.05% (업비트 기본 수수료)
                                </p>
                            </div>

                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                fullWidth
                                loading={loading}
                            >
                                <Play className="w-4 h-4 fill-white" /> 백테스트 실행
                            </Button>
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
                            <LoadingSpinner size="lg" />
                            <p className="text-xl font-bold text-white mb-1 mt-4">{Math.round(progress)}%</p>
                            <p className="text-sm text-primary">{progressMessage}</p>
                        </div>
                    )}

                    {!result && !loading && (
                        <div className="glass-panel flex-1 rounded-2xl flex flex-col items-center justify-center p-16 text-center">
                            <EmptyState
                                icon={<Activity className="w-12 h-12" />}
                                title="분석 대기 중"
                                description="전략을 설정하고 실행 버튼을 눌러주세요."
                            />
                        </div>
                    )}

                    {result && (
                        <>
                            {/* Backtest disclaimer + share button */}
                            <div className="flex items-center justify-between">
                                <p className="text-xs text-gray-500">
                                    * 이 결과는 과거 데이터 시뮬레이션이며 실제 수익을 보장하지 않습니다.
                                </p>
                                {viewingHistoryId && (
                                    <button
                                        onClick={() => {
                                            setShareModal({ historyId: viewingHistoryId });
                                            setShareTitle('백테스트 결과 공유');
                                        }}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-primary hover:bg-primary/10 transition-colors border border-primary/20"
                                    >
                                        <Share2 className="w-3.5 h-3.5" /> 커뮤니티 공유
                                    </button>
                                )}
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div className="glass-panel p-5 rounded-2xl">
                                    <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">누적 수익</p>
                                    <p className={`text-2xl font-bold truncate ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-400'}`}>
                                        ₩{Math.round(result.final_capital - result.initial_capital).toLocaleString()}
                                    </p>
                                    <div className={`inline-flex items-center gap-1 text-xs font-medium mt-2 ${result.final_capital >= result.initial_capital ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {result.final_capital >= result.initial_capital ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                                        {(((result.final_capital - result.initial_capital) / (result.initial_capital || 1)) * 100).toFixed(2)}%
                                    </div>
                                </div>

                                <div className="glass-panel p-5 rounded-2xl">
                                    <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">최종 자산</p>
                                    <p className="text-2xl font-bold text-white truncate">₩{Math.round(result.final_capital).toLocaleString()}</p>
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
                                            {result.trades.map((trade: BacktestTrade, idx: number) => (
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
                                                        <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                                                            {trade.side === 'BUY' ? '매수' : '매도'}
                                                        </Badge>
                                                    </td>
                                                    <td className="px-5 py-4 text-right font-mono text-sm text-gray-300 whitespace-nowrap">
                                                        ₩{Math.round(Number(trade.price ?? 0)).toLocaleString()}
                                                    </td>
                                                    <td className="px-5 py-4 text-right whitespace-nowrap">
                                                        <p className={`font-mono text-sm font-medium ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-600'}`}>
                                                            {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${Math.round(Number(trade.pnl)).toLocaleString()}` : `-₩${Math.round(Math.abs(trade.pnl)).toLocaleString()}`) : '-'}
                                                        </p>
                                                        <p className="text-[10px] text-gray-600 font-mono mt-0.5">
                                                            ₩{Math.round(Number(trade.capital ?? 0)).toLocaleString()}
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
            </div>}
        </PageContainer>
    );
}

function EquityCurveChart({ data }: { data: EquityCurvePoint[] }) {
    if (!data || data.length === 0) return null;

    const values = data.map(d => d.value);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const range = maxVal - minVal || 1;
    const padding = range * 0.1;

    const chartMax = maxVal + padding;
    const chartMin = Math.max(0, minVal - padding);
    const chartRange = chartMax - chartMin || 1;

    const width = 1000;
    const height = 300;

    const divisor = data.length > 1 ? data.length - 1 : 1;
    const points = data.map((d, i) => ({
        x: (i / divisor) * width,
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
                role="img"
                aria-label="자산 성장 추이 차트"
                onMouseMove={(e) => {
                    if (data.length < 2) return;
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
                        left: `${(hoverIndex / divisor) * 100}%`,
                        top: `${(points[hoverIndex].y / height) * 100}%`,
                        transform: `translate(${hoverIndex > divisor / 2 ? '-110%' : '10%'}, -50%)`
                    }}
                >
                    <p className="text-[10px] text-gray-500 mb-1">
                        {new Date(data[hoverIndex].time).toLocaleString()}
                    </p>
                    <p className="text-base font-bold text-white">
                        ₩{Math.round(data[hoverIndex].value).toLocaleString()}
                    </p>
                    <p className={`text-xs font-medium flex items-center gap-1 ${data[hoverIndex].value >= data[0].value ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data[hoverIndex].value >= data[0].value ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {Math.abs(((data[hoverIndex].value - data[0].value) / (data[0].value || 1)) * 100).toFixed(2)}%
                    </p>
                </div>
            )}
        </div>
    );
}
