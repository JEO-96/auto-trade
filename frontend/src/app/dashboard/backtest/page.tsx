'use client';
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Play, Activity, CheckCircle2, TrendingUp, TrendingDown, Settings, History, Share2, X, Trash2, Pencil, Check, ArrowLeft, Save } from 'lucide-react';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import Badge from '@/components/ui/Badge';
import PageContainer from '@/components/ui/PageContainer';
import DeleteConfirmationModal from '@/components/modals/DeleteConfirmationModal';
import { SYMBOLS, BACKTEST_POLL_INTERVAL_MS, TRADE_SIDE, TRADE_SIDE_LABELS, getStrategyLabel, getStrategyTimeframe, TIMEFRAME_LABEL_MAP, STRATEGY_TIMEFRAME_TABS, filterStrategiesByTimeframe, STRATEGY_DEFAULTS } from '@/lib/constants';
import { runPortfolioBacktest, getBacktestStatus, getBacktestHistory, getBacktestHistoryDetail, shareBacktestToCommunity, deleteBacktestHistory, updateBacktestHistoryTitle } from '@/lib/api/backtest';
import { createStrategyFromBacktest } from '@/lib/api/strategies';
import { getBacktestSettings } from '@/lib/api/settings';
import { useStrategies } from '@/lib/useStrategies';
import { getErrorMessage, formatKRW } from '@/lib/utils';
import BacktestComparisonChart from '@/components/BacktestComparisonChart';
import type { BacktestResult, BacktestTrade, EquityCurvePoint, BacktestHistoryItem } from '@/types/backtest';

export default function BacktestPage() {
    const { backtestStrategies } = useStrategies();
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
    const [viewingHistoryMeta, setViewingHistoryMeta] = useState<BacktestHistoryItem | null>(null);
    const [detailMode, setDetailMode] = useState(false);

    // 공유 모달 상태
    const [shareModal, setShareModal] = useState<{ historyId: number } | null>(null);
    const [shareTitle, setShareTitle] = useState('');
    const [shareContent, setShareContent] = useState('');
    const [sharing, setSharing] = useState(false);
    const [shareSuccess, setShareSuccess] = useState(false);

    // 내 전략으로 저장 모달
    const [saveStrategyModal, setSaveStrategyModal] = useState<{ historyId: number; strategyName: string } | null>(null);
    const [saveStrategyName, setSaveStrategyName] = useState('');
    const [savingStrategy, setSavingStrategy] = useState(false);

    // 삭제 확인 모달
    const [deletingHistoryId, setDeletingHistoryId] = useState<number | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // 설정에서 허용된 전략별 타임프레임 매핑 (전략 공개 여부 판단용)
    const [strategyTimeframeMap, setStrategyTimeframeMap] = useState<Record<string, string[]>>(() => {
        const fallback: Record<string, string[]> = {};
        for (const s of backtestStrategies) {
            fallback[s.value] = [getStrategyTimeframe(s.value)];
        }
        return fallback;
    });

    // 타임프레임 필터
    const [backtestTfFilter, setBacktestTfFilter] = useState('all');

    // 인라인 제목 수정
    const [editingTitleId, setEditingTitleId] = useState<number | null>(null);
    const [editTitleValue, setEditTitleValue] = useState('');

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
                // Find meta info from history list
                const meta = historyList.find(h => h.id === id) || null;
                setViewingHistoryMeta(meta);
                setDetailMode(true);
            }
        } catch (err) {
            console.error('백테스트 상세 로드 실패', err);
        }
    };

    const exitDetailMode = () => {
        setDetailMode(false);
        setResult(null);
        setViewingHistoryId(null);
        setViewingHistoryMeta(null);
        setActiveTab('history');
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

    const handleSaveStrategy = async () => {
        if (!saveStrategyModal || !saveStrategyName.trim()) return;
        setSavingStrategy(true);
        try {
            await createStrategyFromBacktest(saveStrategyModal.historyId, saveStrategyName.trim());
            setSaveStrategyModal(null);
            setSaveStrategyName('');
            alert('전략이 저장되었습니다! 봇 생성 시 내 전략에서 선택할 수 있습니다.');
        } catch (err: unknown) {
            const msg = getErrorMessage(err);
            alert(msg || '전략 저장에 실패했습니다.');
        } finally {
            setSavingStrategy(false);
        }
    };

    useEffect(() => {
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, []);

    // 허용된 전략별 타임프레임 로드
    useEffect(() => {
        async function loadSettings() {
            try {
                const settings = await getBacktestSettings();
                if (Object.keys(settings.strategy_timeframes).length > 0) {
                    setStrategyTimeframeMap(settings.strategy_timeframes);
                }
            } catch {
                // 설정 로드 실패 시 전체 표시 (하위 호환)
                const fallback: Record<string, string[]> = {};
                for (const s of backtestStrategies) {
                    fallback[s.value] = [getStrategyTimeframe(s.value)];
                }
                setStrategyTimeframeMap(fallback);
            }
        }
        loadSettings();
    }, [backtestStrategies]);

    const handleSaveTitle = async (id: number) => {
        try {
            await updateBacktestHistoryTitle(id, editTitleValue);
            setHistoryList(prev => prev.map(h => h.id === id ? { ...h, title: editTitleValue } : h));
            setEditingTitleId(null);
        } catch (err) {
            console.error('제목 수정 실패', err);
        }
    };

    const handleDeleteHistory = async (id: number) => {
        setDeleteLoading(true);
        try {
            await deleteBacktestHistory(id);
            setHistoryList(prev => prev.filter(h => h.id !== id));
            setDeletingHistoryId(null);
        } catch (err) {
            console.error('백테스트 기록 삭제 실패', err);
        } finally {
            setDeleteLoading(false);
        }
    };

    useEffect(() => {
        if (activeTab === 'history') fetchHistory();
    }, [activeTab, fetchHistory]);

    const defaultStrategy = 'momentum_elite_1d';
    const [form, setForm] = useState(() => {
        const end = new Date();
        const start = new Date();
        start.setMonth(start.getMonth() - 3);
        return {
            symbols: ['BTC/KRW'],
            timeframe: getStrategyTimeframe(defaultStrategy),
            strategy_name: defaultStrategy,
            initial_capital: 1000000,
            start_date: start.toISOString().split('T')[0],
            end_date: end.toISOString().split('T')[0],
            commission_rate_pct: 0.05,
            period_preset: '3m' as string,
        };
    });

    // 파라미터 튜닝 상태
    const [tuningEnabled, setTuningEnabled] = useState(false);
    const [tuningTrailing, setTuningTrailing] = useState(false);
    const [tuningSl, setTuningSl] = useState(1.5);  // % 단위
    const [tuningTp, setTuningTp] = useState(3.0);  // % 단위
    // 진입 신호 튜닝
    const [tuningRsiPeriod, setTuningRsiPeriod] = useState(14);
    const [tuningRsiThreshold, setTuningRsiThreshold] = useState(60);
    const [tuningAdxThreshold, setTuningAdxThreshold] = useState(20);
    const [tuningVolMultiplier, setTuningVolMultiplier] = useState(1.5);
    const [tuningMacdFast, setTuningMacdFast] = useState(12);
    const [tuningMacdSlow, setTuningMacdSlow] = useState(26);
    const [tuningMacdSignal, setTuningMacdSignal] = useState(9);
    const [tuningRsiUpperLimit, setTuningRsiUpperLimit] = useState(78);
    const [tuningAtrPeriod, setTuningAtrPeriod] = useState(14);
    // 조건 활성화 토글
    const [useRsiFilter, setUseRsiFilter] = useState(true);
    const [useAdxFilter, setUseAdxFilter] = useState(true);
    const [useVolumeFilter, setUseVolumeFilter] = useState(true);
    const [useMacdFilter, setUseMacdFilter] = useState(true);

    const syncTuningDefaults = useCallback((strategyName: string) => {
        const defaults = STRATEGY_DEFAULTS[strategyName];
        if (defaults) {
            setTuningTrailing(defaults.trailing);
            setTuningSl(Math.round(defaults.sl * 10000) / 100);
            setTuningTp(defaults.tp !== null ? Math.round(defaults.tp * 10000) / 100 : 5);
            setTuningRsiPeriod(defaults.rsi_period);
            setTuningRsiThreshold(defaults.rsi_threshold);
            setTuningAdxThreshold(defaults.adx_threshold);
            setTuningVolMultiplier(defaults.volume_multiplier);
            setTuningMacdFast(defaults.macd_fast);
            setTuningMacdSlow(defaults.macd_slow);
            setTuningMacdSignal(defaults.macd_signal);
            setTuningRsiUpperLimit(defaults.rsi_upper_limit);
            setTuningAtrPeriod(defaults.atr_period);
            setUseRsiFilter(true);
            setUseAdxFilter(true);
            setUseVolumeFilter(true);
            setUseMacdFilter(true);
        }
    }, []);

    // 현재 전략에 허용된 전략/타임프레임 목록
    const allowedStrategies = useMemo(
        () => backtestStrategies.filter(s => s.value in strategyTimeframeMap),
        [strategyTimeframeMap, backtestStrategies],
    );
    const filteredBacktestStrategies = useMemo(
        () => filterStrategiesByTimeframe(allowedStrategies, backtestTfFilter),
        [allowedStrategies, backtestTfFilter],
    );
    // 타임프레임 탭 변경 시: 현재 전략이 필터에 없으면 첫 번째 전략으로 자동 선택
    useEffect(() => {
        if (filteredBacktestStrategies.length > 0 && !filteredBacktestStrategies.some(s => s.value === form.strategy_name)) {
            const sorted = [
                ...filteredBacktestStrategies.filter(s => s.status === 'confirmed'),
                ...filteredBacktestStrategies.filter(s => s.status !== 'confirmed'),
            ];
            const first = sorted[0];
            if (first) {
                const tf = getStrategyTimeframe(first.value);
                setForm(prev => ({ ...prev, strategy_name: first.value, timeframe: tf }));
                syncTuningDefaults(first.value);
            }
        }
    }, [filteredBacktestStrategies]);

    // 전략 변경 시 타임프레임 자동 설정 + 튜닝 기본값 동기화
    const prevStrategyRef = useRef(form.strategy_name);
    useEffect(() => {
        if (prevStrategyRef.current !== form.strategy_name) {
            prevStrategyRef.current = form.strategy_name;
            const tf = getStrategyTimeframe(form.strategy_name);
            setForm(prev => prev.timeframe === tf ? prev : { ...prev, timeframe: tf });
            syncTuningDefaults(form.strategy_name);
        }
    }, [form.strategy_name, syncTuningDefaults]);

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
        // 기존 폴링 인터벌이 있으면 정리 (중복 방지)
        if (intervalRef.current) clearInterval(intervalRef.current);
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
            const payload: Record<string, unknown> = {
                symbols: form.symbols,
                timeframe: form.timeframe,
                strategy_name: form.strategy_name,
                limit: null,
                start_date: form.start_date || null,
                end_date: form.end_date || null,
                initial_capital: Number(form.initial_capital),
                commission_rate: form.commission_rate_pct / 100,
            };
            // 튜닝 파라미터 추가
            if (tuningEnabled) {
                payload.custom_sl_pct = tuningSl / 100;  // % → 소수
                payload.custom_trailing = tuningTrailing;
                if (!tuningTrailing) {
                    payload.custom_tp_pct = tuningTp / 100;
                }
                payload.custom_rsi_period = tuningRsiPeriod;
                payload.custom_rsi_threshold = tuningRsiThreshold;
                payload.custom_adx_threshold = tuningAdxThreshold;
                payload.custom_volume_multiplier = tuningVolMultiplier;
                payload.custom_macd_fast = tuningMacdFast;
                payload.custom_macd_slow = tuningMacdSlow;
                payload.custom_macd_signal = tuningMacdSignal;
                payload.custom_rsi_upper_limit = tuningRsiUpperLimit;
                payload.custom_atr_period = tuningAtrPeriod;
                payload.use_rsi_filter = useRsiFilter;
                payload.use_adx_filter = useAdxFilter;
                payload.use_volume_filter = useVolumeFilter;
                payload.use_macd_filter = useMacdFilter;
            }
            const data = await runPortfolioBacktest(payload as unknown as Parameters<typeof runPortfolioBacktest>[0]);

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

    // Detail mode: full-width results view
    if (detailMode && result) {
        const pnlPct = ((result.final_capital - result.initial_capital) / (result.initial_capital || 1)) * 100;
        const isProfit = result.final_capital >= result.initial_capital;
        const metaTitle = viewingHistoryMeta?.title || (viewingHistoryMeta ? getStrategyLabel(viewingHistoryMeta.strategy_name) : '백테스트 결과');

        return (
            <PageContainer>
                {/* 공유 모달 */}
                {shareModal && typeof document !== 'undefined' && createPortal(
                    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShareModal(null)}>
                        <div className="rounded-2xl p-6 w-full max-w-md mx-4 bg-[#0f172a] border border-white/[0.08] shadow-2xl" onClick={(e) => e.stopPropagation()}>
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
                                        className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 mb-3 focus:border-primary/30 transition-colors"
                                    />
                                    <textarea
                                        value={shareContent}
                                        onChange={(e) => setShareContent(e.target.value)}
                                        placeholder="소감이나 분석 내용을 작성하세요 (선택)"
                                        rows={3}
                                        className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 mb-4 resize-none focus:border-primary/30 transition-colors"
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
                    </div>,
                    document.body
                )}

                {/* Header with back button */}
                <header className="mb-6">
                    <button
                        onClick={exitDetailMode}
                        className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors mb-4"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        기록으로 돌아가기
                    </button>
                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white mb-1">{metaTitle}</h1>
                            {viewingHistoryMeta && (
                                <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
                                    <span className="text-gray-400">{getStrategyLabel(viewingHistoryMeta.strategy_name)}</span>
                                    <span>{(viewingHistoryMeta.symbols || []).join(', ')}</span>
                                    <span>{viewingHistoryMeta.timeframe}</span>
                                    {viewingHistoryMeta.start_date && viewingHistoryMeta.end_date && (
                                        <span>{viewingHistoryMeta.start_date} ~ {viewingHistoryMeta.end_date}</span>
                                    )}
                                    {viewingHistoryMeta.commission_rate != null && (
                                        <span>수수료 {(viewingHistoryMeta.commission_rate * 100).toFixed(2)}%</span>
                                    )}
                                    <span>{new Date(viewingHistoryMeta.created_at).toLocaleDateString('ko-KR')}</span>
                                </div>
                            )}
                        </div>
                        <div className="flex gap-2 shrink-0">
                            <button
                                onClick={() => {
                                    setSaveStrategyModal({ historyId: viewingHistoryId!, strategyName: metaTitle || '' });
                                    setSaveStrategyName(`${metaTitle || '커스텀'} 전략`);
                                }}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-emerald-400 hover:bg-emerald-400/10 transition-colors border border-emerald-400/20"
                            >
                                <Save className="w-3.5 h-3.5" /> 내 전략 저장
                            </button>
                            <button
                                onClick={() => {
                                    setShareModal({ historyId: viewingHistoryId! });
                                    setShareTitle(`${metaTitle} 백테스트 결과`);
                                }}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-primary hover:bg-primary/10 transition-colors border border-primary/20"
                            >
                                <Share2 className="w-3.5 h-3.5" /> 커뮤니티 공유
                            </button>
                        </div>
                    </div>
                </header>

                <div className="flex flex-col gap-5">
                    <p className="text-xs text-gray-500">
                        * 이 결과는 과거 데이터 시뮬레이션이며 실제 수익을 보장하지 않습니다.
                    </p>

                    {/* Stats - full width */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="glass-panel p-5 rounded-2xl">
                            <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">누적 수익</p>
                            <p className={`text-2xl font-bold truncate ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                                {isProfit ? '+' : ''}₩{Math.round(result.final_capital - result.initial_capital).toLocaleString()}
                            </p>
                            <div className={`inline-flex items-center gap-1 text-xs font-medium mt-2 ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                                {isProfit ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                                {pnlPct > 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                            </div>
                        </div>

                        <div className="glass-panel p-5 rounded-2xl">
                            <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wider mb-2">초기 투자금</p>
                            <p className="text-2xl font-bold text-white truncate">₩{Math.round(result.initial_capital).toLocaleString()}</p>
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

                    {/* Charts side by side on large screens */}
                    {result.equity_curve && result.equity_curve.length > 0 && (
                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                            {/* Equity Curve */}
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

                            {/* Comparison Chart */}
                            <div className="glass-panel p-6 rounded-2xl">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-base font-bold flex items-center gap-2">
                                        <Activity className="w-4 h-4 text-emerald-400" />
                                        전략 vs 시장 비교
                                    </h3>
                                    <span className="text-[10px] text-gray-500">변동률 (%) 기준</span>
                                </div>
                                <BacktestComparisonChart
                                    equityCurve={result.equity_curve}
                                    priceChanges={result.price_changes}
                                    btcBenchmark={result.btc_benchmark}
                                />
                            </div>
                        </div>
                    )}

                    {/* Trade History - full width */}
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
                                                <p className="text-xs text-gray-400">
                                                    {new Date(trade.time).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '.').replace(/\.$/, '')}
                                                </p>
                                                <p className="text-[10px] text-gray-500 mt-0.5">
                                                    {new Date(trade.time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                                                </p>
                                            </td>
                                            <td className="px-5 py-4">
                                                <span className="font-semibold text-white">{trade.symbol?.split('/')[0]}</span>
                                            </td>
                                            <td className="px-5 py-4 text-center">
                                                <Badge variant={trade.side === TRADE_SIDE.BUY ? 'success' : 'danger'}>
                                                    {TRADE_SIDE_LABELS[trade.side]}
                                                </Badge>
                                            </td>
                                            <td className="px-5 py-4 text-right font-mono text-sm text-gray-400 whitespace-nowrap">
                                                ₩{Math.round(Number(trade.price ?? 0)).toLocaleString()}
                                            </td>
                                            <td className="px-5 py-4 text-right whitespace-nowrap">
                                                <p className={`font-mono text-sm font-medium ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                                                    {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${Math.round(Number(trade.pnl)).toLocaleString()}` : `-₩${Math.round(Math.abs(trade.pnl)).toLocaleString()}`) : '-'}
                                                </p>
                                                <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                                                    ₩{Math.round(Number(trade.capital ?? 0)).toLocaleString()}
                                                </p>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </PageContainer>
        );
    }

    return (
        <PageContainer>
            {/* 삭제 확인 모달 */}
            <DeleteConfirmationModal
                isOpen={deletingHistoryId !== null}
                title="백테스트 기록 삭제"
                message="이 백테스트 기록을 삭제하시겠습니까? 삭제된 기록은 복구할 수 없습니다."
                onConfirm={() => deletingHistoryId !== null && handleDeleteHistory(deletingHistoryId)}
                onCancel={() => setDeletingHistoryId(null)}
                loading={deleteLoading}
            />

            <header className="mb-6">
                <h1 className="text-2xl font-bold mb-1 text-white">전략 백테스팅</h1>
                <p className="text-sm text-gray-500 max-w-xl mb-4">
                    다양한 전략의 과거 성과를 분석하고 포트폴리오 시뮬레이션으로 검증하세요.
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

            {/* 내 전략 저장 모달 */}
            {saveStrategyModal && typeof document !== 'undefined' && createPortal(
                <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setSaveStrategyModal(null)}>
                    <div className="rounded-2xl p-6 w-full max-w-md mx-4 bg-[#0f172a] border border-white/[0.08] shadow-2xl" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-base font-bold text-white">내 전략으로 저장</h3>
                            <button onClick={() => setSaveStrategyModal(null)} className="text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
                        </div>
                        <div className="space-y-3">
                            <input
                                type="text"
                                placeholder="전략 이름 (예: 내 RSI 공격형)"
                                value={saveStrategyName}
                                onChange={(e) => setSaveStrategyName(e.target.value)}
                                maxLength={50}
                                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-emerald-400/50"
                            />
                            <p className="text-xs text-gray-500">저장된 전략은 봇 생성 시 선택할 수 있습니다. (최대 10개)</p>
                            <div className="flex gap-2 justify-end">
                                <Button onClick={handleSaveStrategy} loading={savingStrategy} disabled={!saveStrategyName.trim()} size="sm">
                                    <Save className="w-3.5 h-3.5" /> 저장
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => setSaveStrategyModal(null)}>취소</Button>
                            </div>
                        </div>
                    </div>
                </div>,
                document.body,
            )}

            {/* 공유 모달 - Portal로 body에 직접 렌더링 */}
            {shareModal && typeof document !== 'undefined' && createPortal(
                <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShareModal(null)}>
                    <div className="rounded-2xl p-6 w-full max-w-md mx-4 bg-[#0f172a] border border-white/[0.08] shadow-2xl" onClick={(e) => e.stopPropagation()}>
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
                                    className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 mb-3 focus:border-primary/30 transition-colors"
                                />
                                <textarea
                                    value={shareContent}
                                    onChange={(e) => setShareContent(e.target.value)}
                                    placeholder="소감이나 분석 내용을 작성하세요 (선택)"
                                    rows={3}
                                    className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 mb-4 resize-none focus:border-primary/30 transition-colors"
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
                </div>,
                document.body
            )}

            {/* 기록 탭 */}
            {activeTab === 'history' && (
                <div className="glass-panel rounded-2xl p-6">
                    <h3 className="text-base font-bold text-white mb-5 flex items-center gap-2">
                        <History className="w-5 h-5 text-primary" />
                        백테스트 기록
                    </h3>
                    {historyLoading ? (
                        <div className="flex justify-center py-12"><LoadingSpinner message="기록 불러오는 중..." /></div>
                    ) : historyList.length === 0 ? (
                        <EmptyState icon={<History className="w-12 h-12" />} title="백테스트 기록이 없습니다" description="백테스트를 실행하면 자동으로 기록됩니다." />
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {historyList.map((h) => {
                                const pnlPct = h.final_capital && h.initial_capital
                                    ? ((h.final_capital - h.initial_capital) / h.initial_capital * 100)
                                    : null;
                                const pnlAmount = h.final_capital && h.initial_capital
                                    ? (h.final_capital - h.initial_capital)
                                    : null;
                                const isProfit = pnlPct !== null && pnlPct >= 0;
                                const displayTitle = h.title || getStrategyLabel(h.strategy_name);
                                const isEditingTitle = editingTitleId === h.id;
                                return (
                                    <div
                                        key={h.id}
                                        className={`relative rounded-xl border transition-all hover:scale-[1.01] cursor-pointer ${
                                            h.status === 'completed'
                                                ? isProfit
                                                    ? 'bg-emerald-500/[0.04] border-emerald-500/20 hover:border-emerald-500/40'
                                                    : 'bg-red-500/[0.04] border-red-500/20 hover:border-red-500/40'
                                                : h.status === 'failed'
                                                    ? 'bg-red-500/[0.03] border-red-500/10'
                                                    : 'bg-white/[0.02] border-white/[0.08]'
                                        }`}
                                        onClick={() => h.status === 'completed' && loadHistoryDetail(h.id)}
                                    >
                                        <div className="p-4 group">
                                            {/* 상단: 제목 + 상태 배지 */}
                                            <div className="flex items-start justify-between mb-2">
                                                <div className="min-w-0 flex-1">
                                                    {isEditingTitle ? (
                                                        <div className="flex items-center gap-1">
                                                            <input
                                                                value={editTitleValue}
                                                                onChange={(e) => setEditTitleValue(e.target.value)}
                                                                onKeyDown={(e) => { if (e.key === 'Enter') handleSaveTitle(h.id); if (e.key === 'Escape') setEditingTitleId(null); }}
                                                                className="bg-white/[0.05] border border-primary/30 rounded-lg px-2 py-1 text-xs text-white w-48 focus:outline-none"
                                                                autoFocus
                                                            />
                                                            <button onClick={() => handleSaveTitle(h.id)} className="text-primary hover:text-white transition-colors" title="저장">
                                                                <Check className="w-3.5 h-3.5" />
                                                            </button>
                                                            <button onClick={() => setEditingTitleId(null)} className="text-gray-500 hover:text-white transition-colors" title="취소">
                                                                <X className="w-3.5 h-3.5" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center gap-1.5">
                                                            <p className="text-sm font-bold text-white truncate">{displayTitle}</p>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); setEditingTitleId(h.id); setEditTitleValue(h.title || ''); }}
                                                                className="text-gray-500 hover:text-primary transition-colors opacity-0 group-hover:opacity-100"
                                                                title="제목 수정"
                                                            >
                                                                <Pencil className="w-3 h-3" />
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                                <Badge variant={h.status === 'completed' ? 'success' : h.status === 'failed' ? 'danger' : 'warning'}>
                                                    {h.status === 'completed' ? '완료' : h.status === 'failed' ? '실패' : '진행중'}
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-3 text-[11px] text-gray-500 flex-wrap mb-3">
                                                <span className="text-gray-400">{getStrategyLabel(h.strategy_name)}</span>
                                                <span>{(h.symbols || []).join(', ')}</span>
                                                <span>{h.timeframe}</span>
                                                <span>₩{h.initial_capital.toLocaleString()}</span>
                                                {h.start_date && h.end_date && (
                                                    <span>{h.start_date} ~ {h.end_date}</span>
                                                )}
                                                {h.commission_rate != null && (
                                                    <span>수수료 {(h.commission_rate * 100).toFixed(2)}%</span>
                                                )}
                                                <span>{new Date(h.created_at).toLocaleDateString('ko-KR')}</span>
                                            </div>

                                            {/* 수익률 & 핵심 지표 */}
                                            {h.status === 'completed' && pnlPct !== null ? (
                                                <div className="flex items-end justify-between">
                                                    <div>
                                                        <div className={`text-xl font-extrabold tracking-tight ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                                                            {isProfit ? '+' : ''}{pnlPct.toFixed(2)}%
                                                        </div>
                                                        <p className={`text-xs mt-0.5 ${isProfit ? 'text-emerald-400/60' : 'text-red-400/60'}`}>
                                                            {isProfit ? '+' : ''}{pnlAmount !== null ? `₩${Math.round(pnlAmount).toLocaleString()}` : ''}
                                                        </p>
                                                    </div>
                                                    <div className="text-right space-y-0.5">
                                                        <p className="text-[11px] text-gray-400">
                                                            <span className="text-gray-500">투자금</span>{' '}
                                                            <span className="font-semibold text-gray-400">₩{h.initial_capital.toLocaleString()}</span>
                                                        </p>
                                                        <p className="text-[11px] text-gray-400">
                                                            <span className="text-gray-500">거래</span>{' '}
                                                            <span className="font-semibold text-gray-400">{h.total_trades}회</span>
                                                        </p>
                                                    </div>
                                                </div>
                                            ) : h.status === 'failed' ? (
                                                <p className="text-xs text-red-400/70">백테스트 실행에 실패했습니다</p>
                                            ) : (
                                                <p className="text-xs text-yellow-400/70">백테스트 진행 중...</p>
                                            )}
                                        </div>

                                        {/* 하단 액션 바 */}
                                        <div className="flex items-center justify-end gap-1 px-3 py-2 border-t border-white/[0.04]" onClick={(e) => e.stopPropagation()}>
                                            {h.status === 'completed' && (
                                                <>
                                                    <button
                                                        onClick={() => loadHistoryDetail(h.id)}
                                                        className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-gray-400 hover:text-white hover:bg-white/[0.02] transition-colors"
                                                    >
                                                        상세보기
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            setShareModal({ historyId: h.id });
                                                            setShareTitle(`${getStrategyLabel(h.strategy_name)} 백테스트 결과 (${(h.symbols || []).join(', ')})`);
                                                        }}
                                                        className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-primary hover:bg-primary/10 transition-colors flex items-center gap-1"
                                                    >
                                                        <Share2 className="w-3 h-3" /> 공유
                                                    </button>
                                                </>
                                            )}
                                            <button
                                                onClick={() => setDeletingHistoryId(h.id)}
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
                                                : 'bg-white/[0.02] border-white/[0.08] text-gray-500 hover:border-white/[0.08]'
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
                                <div className="flex gap-1 mb-2">
                                    {STRATEGY_TIMEFRAME_TABS.map(tab => (
                                        <button
                                            key={tab.value}
                                            type="button"
                                            onClick={() => setBacktestTfFilter(tab.value)}
                                            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all border ${
                                                backtestTfFilter === tab.value
                                                    ? 'bg-primary/10 border-primary/30 text-primary'
                                                    : 'bg-white/[0.02] border-white/[0.08] text-gray-500 hover:text-gray-400'
                                            }`}
                                        >
                                            {tab.label}
                                        </button>
                                    ))}
                                </div>
                                <select
                                    name="strategy_name"
                                    value={form.strategy_name}
                                    onChange={handleChange}
                                    className="w-full bg-white/[0.02] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-medium text-white appearance-none cursor-pointer focus:border-primary/30 transition-colors [&>option]:bg-[--select-bg] [&>option]:text-white"
                                >
                                    {[
                                        ...filteredBacktestStrategies.filter(s => s.status === 'confirmed'),
                                        ...filteredBacktestStrategies.filter(s => s.status !== 'confirmed'),
                                    ].map(s => (
                                        <option key={s.value} value={s.value}>
                                            {s.status === 'confirmed' ? `✅ ${s.label}` : `🧪 ${s.label}`}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Timeframe (자동 설정) */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">캔들 주기</label>
                                <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl px-4 py-3 flex items-center gap-2">
                                    <span className="text-sm font-semibold text-primary">{TIMEFRAME_LABEL_MAP[form.timeframe] || form.timeframe}</span>
                                    <span className="text-[10px] text-gray-500">(전략에 의해 자동 설정)</span>
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
                                                    : 'bg-white/[0.02] border-white/[0.08] text-gray-500 hover:text-gray-400 hover:border-white/[0.08]'
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
                                            className="w-full bg-white/[0.02] border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs text-white focus:border-primary/30 transition-colors [color-scheme:dark]"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-[10px] text-gray-500 font-medium mb-1 block">종료일</label>
                                        <input
                                            type="date"
                                            name="end_date"
                                            value={form.end_date}
                                            onChange={handleChange}
                                            className="w-full bg-white/[0.02] border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs text-white focus:border-primary/30 transition-colors [color-scheme:dark]"
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
                                        className="w-full bg-white/[0.02] border border-white/[0.08] rounded-xl pl-10 pr-4 py-3 text-lg font-bold text-white focus:border-primary/30 transition-colors font-mono"
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
                                    className="w-full bg-white/[0.02] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-medium text-white focus:border-primary/30 transition-colors font-mono"
                                    placeholder="0.05"
                                />
                                <p className="text-[10px] text-gray-500 mt-1.5">
                                    예: 0.05 = 0.05% (업비트 기본 수수료)
                                </p>
                            </div>

                            {/* 파라미터 튜닝 */}
                            <div className="border border-white/[0.06] rounded-xl overflow-hidden">
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (!tuningEnabled) syncTuningDefaults(form.strategy_name);
                                        setTuningEnabled(!tuningEnabled);
                                    }}
                                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
                                >
                                    <span className="flex items-center gap-2 text-xs font-semibold text-gray-400">
                                        <Settings className="w-3.5 h-3.5" />
                                        파라미터 튜닝
                                    </span>
                                    <div className={`w-8 h-4.5 rounded-full transition-colors relative ${tuningEnabled ? 'bg-primary' : 'bg-white/10'}`}>
                                        <div className={`absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white shadow transition-transform ${tuningEnabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                                    </div>
                                </button>
                                {tuningEnabled && (
                                    <div className="px-4 pb-4 pt-2 space-y-4 border-t border-white/[0.06]">
                                        {/* 청산 모드 */}
                                        <div>
                                            <label className="text-[10px] text-gray-500 font-medium mb-2 block uppercase tracking-wider">청산 모드</label>
                                            <div className="grid grid-cols-2 gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => setTuningTrailing(false)}
                                                    className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${!tuningTrailing ? 'bg-primary/15 text-primary border border-primary/30' : 'bg-white/[0.02] text-gray-500 border border-white/[0.06] hover:text-white'}`}
                                                >
                                                    고정 SL/TP
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => setTuningTrailing(true)}
                                                    className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${tuningTrailing ? 'bg-primary/15 text-primary border border-primary/30' : 'bg-white/[0.02] text-gray-500 border border-white/[0.06] hover:text-white'}`}
                                                >
                                                    트레일링 스탑
                                                </button>
                                            </div>
                                        </div>

                                        {/* 손절률 */}
                                        <div>
                                            <div className="flex items-center justify-between mb-1.5">
                                                <label className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">
                                                    {tuningTrailing ? '트레일링 스탑' : '손절률 (SL)'}
                                                </label>
                                                <span className="text-xs font-bold text-red-400 font-mono">{tuningSl.toFixed(1)}%</span>
                                            </div>
                                            <input
                                                type="range"
                                                min="0.5"
                                                max="10"
                                                step="0.5"
                                                value={tuningSl}
                                                onChange={(e) => setTuningSl(Number(e.target.value))}
                                                className="w-full h-1.5 rounded-full appearance-none bg-white/10 accent-red-400 cursor-pointer"
                                            />
                                            <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
                                                <span>0.5%</span>
                                                <span>10%</span>
                                            </div>
                                        </div>

                                        {/* 익절률 (트레일링 아닐 때만) */}
                                        {!tuningTrailing && (
                                            <div>
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <label className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">익절률 (TP)</label>
                                                    <span className="text-xs font-bold text-emerald-400 font-mono">{tuningTp.toFixed(1)}%</span>
                                                </div>
                                                <input
                                                    type="range"
                                                    min="1"
                                                    max="50"
                                                    step="1"
                                                    value={tuningTp}
                                                    onChange={(e) => setTuningTp(Number(e.target.value))}
                                                    className="w-full h-1.5 rounded-full appearance-none bg-white/10 accent-emerald-400 cursor-pointer"
                                                />
                                                <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
                                                    <span>1%</span>
                                                    <span>50%</span>
                                                </div>
                                            </div>
                                        )}

                                        {tuningTrailing && (
                                            <p className="text-[10px] text-gray-500 bg-white/[0.02] rounded-lg px-3 py-2">
                                                트레일링 모드: 최고가 대비 {tuningSl.toFixed(1)}% 하락 시 청산. 익절 목표 없이 추세를 끝까지 추종합니다.
                                            </p>
                                        )}

                                        {/* 진입 신호 조건 설정 */}
                                        <div className="pt-3 border-t border-white/[0.06] space-y-3">
                                            <label className="text-[10px] text-gray-500 font-medium block uppercase tracking-wider">진입 조건 설정</label>

                                            {/* RSI 필터 */}
                                            <div className={`rounded-lg border transition-colors ${useRsiFilter ? 'border-blue-500/20 bg-blue-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                                                <button type="button" onClick={() => setUseRsiFilter(!useRsiFilter)}
                                                    className="w-full flex items-center justify-between px-3 py-2">
                                                    <span className={`text-[11px] font-semibold ${useRsiFilter ? 'text-blue-400' : 'text-gray-600'}`}>RSI 필터</span>
                                                    <div className={`w-7 h-4 rounded-full transition-colors relative ${useRsiFilter ? 'bg-blue-500' : 'bg-white/10'}`}>
                                                        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useRsiFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                                    </div>
                                                </button>
                                                {useRsiFilter && (
                                                    <div className="px-3 pb-2.5 space-y-2">
                                                        <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">기간</span><span className="text-[10px] font-bold text-blue-400 font-mono">{tuningRsiPeriod}</span></div>
                                                            <input type="range" min="7" max="30" step="1" value={tuningRsiPeriod} onChange={(e) => setTuningRsiPeriod(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-blue-400 cursor-pointer" /></div>
                                                        <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">진입 기준</span><span className="text-[10px] font-bold text-blue-400 font-mono">{tuningRsiThreshold}</span></div>
                                                            <input type="range" min="30" max="80" step="1" value={tuningRsiThreshold} onChange={(e) => setTuningRsiThreshold(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-blue-400 cursor-pointer" /></div>
                                                        <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">과매수 상한</span><span className="text-[10px] font-bold text-blue-400 font-mono">{tuningRsiUpperLimit}</span></div>
                                                            <input type="range" min="65" max="95" step="1" value={tuningRsiUpperLimit} onChange={(e) => setTuningRsiUpperLimit(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-blue-400 cursor-pointer" /></div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* MACD 필터 */}
                                            <div className={`rounded-lg border transition-colors ${useMacdFilter ? 'border-cyan-500/20 bg-cyan-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                                                <button type="button" onClick={() => setUseMacdFilter(!useMacdFilter)}
                                                    className="w-full flex items-center justify-between px-3 py-2">
                                                    <span className={`text-[11px] font-semibold ${useMacdFilter ? 'text-cyan-400' : 'text-gray-600'}`}>MACD 필터</span>
                                                    <div className={`w-7 h-4 rounded-full transition-colors relative ${useMacdFilter ? 'bg-cyan-500' : 'bg-white/10'}`}>
                                                        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useMacdFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                                    </div>
                                                </button>
                                                {useMacdFilter && (
                                                    <div className="px-3 pb-2.5 space-y-2">
                                                        <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">단기 (Fast)</span><span className="text-[10px] font-bold text-cyan-400 font-mono">{tuningMacdFast}</span></div>
                                                            <input type="range" min="5" max="20" step="1" value={tuningMacdFast} onChange={(e) => setTuningMacdFast(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-cyan-400 cursor-pointer" /></div>
                                                        <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">장기 (Slow)</span><span className="text-[10px] font-bold text-cyan-400 font-mono">{tuningMacdSlow}</span></div>
                                                            <input type="range" min="15" max="40" step="1" value={tuningMacdSlow} onChange={(e) => setTuningMacdSlow(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-cyan-400 cursor-pointer" /></div>
                                                        <div><div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">시그널</span><span className="text-[10px] font-bold text-cyan-400 font-mono">{tuningMacdSignal}</span></div>
                                                            <input type="range" min="3" max="15" step="1" value={tuningMacdSignal} onChange={(e) => setTuningMacdSignal(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-cyan-400 cursor-pointer" /></div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* ADX 필터 */}
                                            <div className={`rounded-lg border transition-colors ${useAdxFilter ? 'border-purple-500/20 bg-purple-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                                                <button type="button" onClick={() => setUseAdxFilter(!useAdxFilter)}
                                                    className="w-full flex items-center justify-between px-3 py-2">
                                                    <span className={`text-[11px] font-semibold ${useAdxFilter ? 'text-purple-400' : 'text-gray-600'}`}>ADX 추세 필터</span>
                                                    <div className={`w-7 h-4 rounded-full transition-colors relative ${useAdxFilter ? 'bg-purple-500' : 'bg-white/10'}`}>
                                                        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useAdxFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                                    </div>
                                                </button>
                                                {useAdxFilter && (
                                                    <div className="px-3 pb-2.5">
                                                        <div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">추세 강도 기준</span><span className="text-[10px] font-bold text-purple-400 font-mono">{tuningAdxThreshold}</span></div>
                                                        <input type="range" min="10" max="40" step="1" value={tuningAdxThreshold} onChange={(e) => setTuningAdxThreshold(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-purple-400 cursor-pointer" />
                                                    </div>
                                                )}
                                            </div>

                                            {/* 거래량 필터 */}
                                            <div className={`rounded-lg border transition-colors ${useVolumeFilter ? 'border-amber-500/20 bg-amber-500/[0.03]' : 'border-white/[0.04] bg-white/[0.01]'}`}>
                                                <button type="button" onClick={() => setUseVolumeFilter(!useVolumeFilter)}
                                                    className="w-full flex items-center justify-between px-3 py-2">
                                                    <span className={`text-[11px] font-semibold ${useVolumeFilter ? 'text-amber-400' : 'text-gray-600'}`}>거래량 필터</span>
                                                    <div className={`w-7 h-4 rounded-full transition-colors relative ${useVolumeFilter ? 'bg-amber-500' : 'bg-white/10'}`}>
                                                        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform ${useVolumeFilter ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                                                    </div>
                                                </button>
                                                {useVolumeFilter && (
                                                    <div className="px-3 pb-2.5">
                                                        <div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">평균 대비 배수</span><span className="text-[10px] font-bold text-amber-400 font-mono">{tuningVolMultiplier.toFixed(1)}x</span></div>
                                                        <input type="range" min="0.5" max="3.0" step="0.1" value={tuningVolMultiplier} onChange={(e) => setTuningVolMultiplier(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-amber-400 cursor-pointer" />
                                                    </div>
                                                )}
                                            </div>

                                            {/* ATR 기간 */}
                                            <div className="px-1">
                                                <div className="flex justify-between mb-0.5"><span className="text-[9px] text-gray-500">ATR 변동성 기간</span><span className="text-[10px] font-bold text-gray-400 font-mono">{tuningAtrPeriod}</span></div>
                                                <input type="range" min="7" max="30" step="1" value={tuningAtrPeriod} onChange={(e) => setTuningAtrPeriod(Number(e.target.value))} className="w-full h-1 rounded-full appearance-none bg-white/10 accent-gray-400 cursor-pointer" />
                                            </div>
                                        </div>

                                        {/* 기본값 초기화 */}
                                        <button
                                            type="button"
                                            onClick={() => syncTuningDefaults(form.strategy_name)}
                                            className="text-[10px] text-gray-500 hover:text-primary transition-colors underline underline-offset-2"
                                        >
                                            전략 기본값으로 초기화
                                        </button>
                                    </div>
                                )}
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
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => {
                                                setSaveStrategyModal({ historyId: viewingHistoryId, strategyName: '' });
                                                setSaveStrategyName('커스텀 전략');
                                            }}
                                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-emerald-400 hover:bg-emerald-400/10 transition-colors border border-emerald-400/20"
                                        >
                                            <Save className="w-3.5 h-3.5" /> 내 전략 저장
                                        </button>
                                        <button
                                            onClick={() => {
                                                setShareModal({ historyId: viewingHistoryId });
                                                setShareTitle('백테스트 결과 공유');
                                            }}
                                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-primary hover:bg-primary/10 transition-colors border border-primary/20"
                                        >
                                            <Share2 className="w-3.5 h-3.5" /> 커뮤니티 공유
                                        </button>
                                    </div>
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

                            {/* Comparison Chart: Strategy vs Coin Prices */}
                            {result.equity_curve && result.equity_curve.length > 0 && (
                                <div className="glass-panel p-6 rounded-2xl">
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="text-base font-bold flex items-center gap-2">
                                            <Activity className="w-4 h-4 text-emerald-400" />
                                            전략 vs 시장 비교
                                        </h3>
                                        <span className="text-[10px] text-gray-500">변동률 (%) 기준</span>
                                    </div>
                                    <BacktestComparisonChart
                                        equityCurve={result.equity_curve}
                                        priceChanges={result.price_changes}
                                        btcBenchmark={result.btc_benchmark}
                                    />
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
                                                        <p className="text-xs text-gray-400">
                                                            {new Date(trade.time).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '.').replace(/\.$/, '')}
                                                        </p>
                                                        <p className="text-[10px] text-gray-500 mt-0.5">
                                                            {new Date(trade.time).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                                                        </p>
                                                    </td>
                                                    <td className="px-5 py-4">
                                                        <span className="font-semibold text-white">{trade.symbol?.split('/')[0]}</span>
                                                    </td>
                                                    <td className="px-5 py-4 text-center">
                                                        <Badge variant={trade.side === TRADE_SIDE.BUY ? 'success' : 'danger'}>
                                                            {TRADE_SIDE_LABELS[trade.side]}
                                                        </Badge>
                                                    </td>
                                                    <td className="px-5 py-4 text-right font-mono text-sm text-gray-400 whitespace-nowrap">
                                                        ₩{Math.round(Number(trade.price ?? 0)).toLocaleString()}
                                                    </td>
                                                    <td className="px-5 py-4 text-right whitespace-nowrap">
                                                        <p className={`font-mono text-sm font-medium ${trade.pnl > 0 ? 'text-emerald-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                                                            {trade.pnl !== 0 ? (trade.pnl > 0 ? `+₩${Math.round(Number(trade.pnl)).toLocaleString()}` : `-₩${Math.round(Math.abs(trade.pnl)).toLocaleString()}`) : '-'}
                                                        </p>
                                                        <p className="text-[10px] text-gray-500 font-mono mt-0.5">
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
