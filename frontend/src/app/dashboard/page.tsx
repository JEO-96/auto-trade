'use client';
import { useState, useEffect, useCallback } from 'react';
import {
    Play, StopCircle, Activity, Settings2, BarChart2, AlertTriangle,
    TrendingUp, TrendingDown, Clock, Wallet, ArrowUpRight, Zap,
    ListFilter, Plus, Trash2, X, Edit3,
} from 'lucide-react';
import RiskDisclaimerModal from '@/components/RiskDisclaimerModal';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Input, { SelectInput } from '@/components/ui/Input';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import PageContainer from '@/components/ui/PageContainer';
import { SYMBOLS, BOT_POLL_INTERVAL_MS, BOT_STRATEGIES, BOT_TIMEFRAMES } from '@/lib/constants';
import {
    getBotList, getBotStatus, getBotLogs, startBot, stopBot,
    createBot, updateBot, deleteBot,
} from '@/lib/api/bot';
import { getUpbitBalance, type BalanceItem } from '@/lib/api/keys';
import { getErrorMessage } from '@/lib/utils';
import type { BotConfig, TradeLog } from '@/types/bot';

type ModalMode = 'create' | 'edit';

const STRATEGY_LABEL_MAP: Record<string, string> = {};
for (const s of BOT_STRATEGIES) {
    STRATEGY_LABEL_MAP[s.value] = s.label;
}

const TIMEFRAME_LABEL_MAP: Record<string, string> = {};
for (const t of BOT_TIMEFRAMES) {
    TIMEFRAME_LABEL_MAP[t.value] = t.label;
}

const defaultFormState = {
    symbols: ['BTC/KRW'] as string[],
    timeframe: '1h',
    strategy_name: 'momentum_breakout_pro_stable',
    paper_trading_mode: true,
    allocated_capital: 1000000,
};

export default function DashboardPage() {
    // Bot list state
    const [bots, setBots] = useState<BotConfig[]>([]);
    const [botStatuses, setBotStatuses] = useState<Record<number, boolean>>({});
    const [loading, setLoading] = useState(true);

    // Selected bot for trade logs
    const [selectedBotId, setSelectedBotId] = useState<number | null>(null);
    const [tradeLogs, setTradeLogs] = useState<TradeLog[]>([]);

    // Risk modal
    const [showRiskModal, setShowRiskModal] = useState(false);
    const [pendingStartBotId, setPendingStartBotId] = useState<number | null>(null);

    // Create/Edit modal
    const [showBotModal, setShowBotModal] = useState(false);
    const [modalMode, setModalMode] = useState<ModalMode>('create');
    const [editingBotId, setEditingBotId] = useState<number | null>(null);
    const [formData, setFormData] = useState<typeof defaultFormState>({ ...defaultFormState });
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    // Delete confirm
    const [deletingBotId, setDeletingBotId] = useState<number | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Action loading per bot
    const [actionLoading, setActionLoading] = useState<Record<number, boolean>>({});

    // Upbit balance
    const [balances, setBalances] = useState<BalanceItem[]>([]);

    const fetchBots = useCallback(async () => {
        try {
            const list = await getBotList();
            setBots(list);

            // Fetch statuses for all bots
            const statuses: Record<number, boolean> = {};
            await Promise.all(
                list.map(async (bot) => {
                    try {
                        const status = await getBotStatus(bot.id);
                        statuses[bot.id] = status.bot_status === 'Running';
                    } catch {
                        statuses[bot.id] = false;
                    }
                })
            );
            setBotStatuses(statuses);

            // Select first bot if none selected
            if (list.length > 0) {
                setSelectedBotId((prev) => {
                    if (prev === null || !list.find((b) => b.id === prev)) {
                        return list[0].id;
                    }
                    return prev;
                });
            }
        } catch (err) {
            console.error('봇 목록을 불러올 수 없습니다', err);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchLogs = useCallback(async (botId: number) => {
        try {
            const logs = await getBotLogs(botId);
            setTradeLogs(logs);
        } catch (err) {
            console.error('로그를 불러올 수 없습니다', err);
        }
    }, []);

    const fetchBalance = useCallback(async () => {
        try {
            const data = await getUpbitBalance();
            setBalances(data);
        } catch {
            // API 키 미등록 등 — 무시
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchBots();
        fetchBalance();
    }, [fetchBots, fetchBalance]);

    // Fetch logs when selected bot changes
    useEffect(() => {
        if (selectedBotId !== null) {
            fetchLogs(selectedBotId);
        }
    }, [selectedBotId, fetchLogs]);

    // Polling
    useEffect(() => {
        const interval = setInterval(() => {
            fetchBots();
            if (selectedBotId !== null) {
                fetchLogs(selectedBotId);
            }
        }, BOT_POLL_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [fetchBots, fetchLogs, selectedBotId]);

    // --- Actions ---

    const handleStartClick = (botId: number) => {
        setPendingStartBotId(botId);
        setShowRiskModal(true);
    };

    const handleRiskConfirm = async () => {
        setShowRiskModal(false);
        if (pendingStartBotId === null) return;
        const botId = pendingStartBotId;
        setPendingStartBotId(null);
        setActionLoading((prev) => ({ ...prev, [botId]: true }));
        try {
            await startBot(botId);
            setBotStatuses((prev) => ({ ...prev, [botId]: true }));
        } catch (err) {
            alert(getErrorMessage(err, '서버 연결에 실패했거나 권한이 없습니다.'));
        } finally {
            setActionLoading((prev) => ({ ...prev, [botId]: false }));
        }
    };

    const handleStop = async (botId: number) => {
        setActionLoading((prev) => ({ ...prev, [botId]: true }));
        try {
            await stopBot(botId);
            setBotStatuses((prev) => ({ ...prev, [botId]: false }));
        } catch (err) {
            alert(getErrorMessage(err, '서버 연결에 실패했거나 권한이 없습니다.'));
        } finally {
            setActionLoading((prev) => ({ ...prev, [botId]: false }));
        }
    };

    const openCreateModal = () => {
        setModalMode('create');
        setEditingBotId(null);
        setFormData({ ...defaultFormState });
        setFormError(null);
        setShowBotModal(true);
    };

    const openEditModal = (bot: BotConfig) => {
        setModalMode('edit');
        setEditingBotId(bot.id);
        setFormData({
            symbols: [bot.symbol],
            timeframe: bot.timeframe,
            strategy_name: bot.strategy_name,
            paper_trading_mode: bot.paper_trading_mode,
            allocated_capital: bot.allocated_capital,
        });
        setFormError(null);
        setShowBotModal(true);
    };

    const handleFormSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormLoading(true);
        setFormError(null);
        try {
            if (modalMode === 'create') {
                if (formData.symbols.length === 0) {
                    setFormError('심볼을 1개 이상 선택해주세요.');
                    setFormLoading(false);
                    return;
                }
                for (const symbol of formData.symbols) {
                    await createBot({
                        symbol,
                        timeframe: formData.timeframe,
                        strategy_name: formData.strategy_name,
                        paper_trading_mode: formData.paper_trading_mode,
                        allocated_capital: formData.allocated_capital,
                    });
                }
            } else if (editingBotId !== null) {
                await updateBot(editingBotId, {
                    symbol: formData.symbols[0],
                    timeframe: formData.timeframe,
                    strategy_name: formData.strategy_name,
                    paper_trading_mode: formData.paper_trading_mode,
                    allocated_capital: formData.allocated_capital,
                });
            }
            setShowBotModal(false);
            await fetchBots();
        } catch (err) {
            setFormError(getErrorMessage(err, '봇 저장에 실패했습니다.'));
        } finally {
            setFormLoading(false);
        }
    };

    const handleDelete = async (botId: number) => {
        setDeleteLoading(true);
        try {
            await deleteBot(botId);
            setDeletingBotId(null);
            if (selectedBotId === botId) {
                setSelectedBotId(null);
                setTradeLogs([]);
            }
            await fetchBots();
        } catch (err) {
            alert(getErrorMessage(err, '봇 삭제에 실패했습니다.'));
        } finally {
            setDeleteLoading(false);
        }
    };

    // --- Computed ---
    const selectedBot = bots.find((b) => b.id === selectedBotId) ?? null;
    const selectedBotRunning = selectedBotId !== null ? !!botStatuses[selectedBotId] : false;
    const activeBotCount = Object.values(botStatuses).filter(Boolean).length;

    // 실매매 봇이 이미 있는지 체크 (수정 중인 봇은 제외)
    const hasLiveBot = bots.some((b) => !b.paper_trading_mode && b.id !== editingBotId);
    const liveBotLimitReached = hasLiveBot;

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[80vh]">
                <LoadingSpinner message="데이터 불러오는 중..." />
            </div>
        );
    }

    return (
        <PageContainer>
            {/* Risk Disclaimer Modal */}
            {showRiskModal && (
                <RiskDisclaimerModal
                    onConfirm={handleRiskConfirm}
                    onCancel={() => {
                        setShowRiskModal(false);
                        setPendingStartBotId(null);
                    }}
                />
            )}

            {/* Delete Confirmation Modal */}
            {deletingBotId !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4" role="dialog" aria-modal="true">
                    <div className="w-full max-w-sm bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-9 h-9 bg-red-500/10 rounded-xl flex items-center justify-center border border-red-500/20">
                                <Trash2 className="w-5 h-5 text-red-400" />
                            </div>
                            <h3 className="text-base font-bold text-white">봇 삭제</h3>
                        </div>
                        <p className="text-sm text-gray-400 mb-6">
                            이 봇을 삭제하시겠습니까? 삭제된 봇은 복구할 수 없습니다.
                        </p>
                        <div className="flex gap-3">
                            <Button
                                variant="ghost"
                                size="md"
                                className="flex-1"
                                onClick={() => setDeletingBotId(null)}
                                disabled={deleteLoading}
                            >
                                취소
                            </Button>
                            <Button
                                variant="danger"
                                size="md"
                                className="flex-1"
                                onClick={() => handleDelete(deletingBotId)}
                                loading={deleteLoading}
                            >
                                <Trash2 className="w-4 h-4" />
                                삭제
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create/Edit Bot Modal */}
            {showBotModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4" role="dialog" aria-modal="true">
                    <div className="w-full max-w-md bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl">
                        <div className="flex items-center justify-between p-6 border-b border-white/[0.06]">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">
                                    {modalMode === 'create' ? <Plus className="w-5 h-5 text-primary" /> : <Edit3 className="w-5 h-5 text-primary" />}
                                </div>
                                <h2 className="text-base font-bold text-white">
                                    {modalMode === 'create' ? '새 봇 만들기' : '봇 설정 수정'}
                                </h2>
                            </div>
                            <button onClick={() => setShowBotModal(false)} aria-label="닫기" className="text-gray-500 hover:text-gray-300 transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleFormSubmit} className="p-6 space-y-5">
                            {formError && (
                                <div className="p-3 rounded-xl bg-red-500/[0.06] border border-red-500/20 text-red-400 text-sm">
                                    {formError}
                                </div>
                            )}

                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">
                                    심볼 (Symbol) {modalMode === 'create' && <span className="text-gray-600">— 복수 선택 가능</span>}
                                </label>
                                <div className="grid grid-cols-2 gap-2">
                                    {SYMBOLS.map(s => {
                                        const isSelected = formData.symbols.includes(s);
                                        return (
                                            <button
                                                key={s}
                                                type="button"
                                                onClick={() => {
                                                    if (modalMode === 'edit') {
                                                        setFormData({ ...formData, symbols: [s] });
                                                    } else {
                                                        setFormData({
                                                            ...formData,
                                                            symbols: isSelected
                                                                ? formData.symbols.filter(sym => sym !== s)
                                                                : [...formData.symbols, s],
                                                        });
                                                    }
                                                }}
                                                className={`py-2.5 rounded-xl text-xs font-semibold transition-all border ${
                                                    isSelected
                                                        ? 'bg-primary/10 border-primary/30 text-primary'
                                                        : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10 hover:text-gray-300'
                                                }`}
                                            >
                                                {s.split('/')[0]} <span className="opacity-40 text-[10px]">/ KRW</span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <SelectInput
                                type="select"
                                label="캔들 주기 (Timeframe)"
                                value={formData.timeframe}
                                onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                            >
                                {BOT_TIMEFRAMES.map((tf) => (
                                    <option key={tf.value} value={tf.value}>{tf.label}</option>
                                ))}
                            </SelectInput>

                            <SelectInput
                                type="select"
                                label="전략 (Strategy)"
                                value={formData.strategy_name}
                                onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
                            >
                                {BOT_STRATEGIES.map((s) => (
                                    <option key={s.value} value={s.value}>{s.label}</option>
                                ))}
                            </SelectInput>

                            {/* Trading mode toggle */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">매매 모드</label>
                                <div className="grid grid-cols-2 gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setFormData({ ...formData, paper_trading_mode: true })}
                                        className={`py-3 rounded-xl text-sm font-semibold transition-all border ${
                                            formData.paper_trading_mode
                                                ? 'bg-primary/10 border-primary/30 text-primary'
                                                : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10'
                                        }`}
                                    >
                                        모의투자
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            if (!liveBotLimitReached) {
                                                setFormData({ ...formData, paper_trading_mode: false });
                                            }
                                        }}
                                        disabled={liveBotLimitReached}
                                        className={`py-3 rounded-xl text-sm font-semibold transition-all border ${
                                            !formData.paper_trading_mode
                                                ? 'bg-red-500/10 border-red-500/30 text-red-400'
                                                : liveBotLimitReached
                                                    ? 'bg-white/[0.01] border-white/[0.04] text-gray-700 cursor-not-allowed'
                                                    : 'bg-white/[0.02] border-white/[0.06] text-gray-500 hover:border-white/10'
                                        }`}
                                    >
                                        실매매
                                    </button>
                                </div>
                                {liveBotLimitReached && formData.paper_trading_mode && (
                                    <div className="mt-3 flex items-start gap-2.5 p-3 bg-yellow-500/[0.06] rounded-xl border border-yellow-500/15">
                                        <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
                                        <p className="text-xs text-yellow-400/90 leading-relaxed">
                                            실매매 봇은 1개만 운영할 수 있습니다. 기존 실매매 봇을 삭제하거나 모의투자로 전환하세요.
                                        </p>
                                    </div>
                                )}
                                {!formData.paper_trading_mode && (
                                    <div className="mt-3 flex items-start gap-2.5 p-3 bg-red-500/[0.06] rounded-xl border border-red-500/15">
                                        <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                                        <p className="text-xs text-red-400/90 leading-relaxed">
                                            실매매 모드에서는 실제 자금이 거래됩니다.
                                            원금 손실 위험이 있으니 신중하게 설정하세요.
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Capital */}
                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-1.5 block">운용 자본 (KRW)</label>
                                <div className="relative">
                                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-semibold text-sm">&#8361;</div>
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        value={Number(formData.allocated_capital ?? 0).toLocaleString()}
                                        onChange={(e) => {
                                            const val = e.target.value.replace(/[^0-9]/g, '');
                                            setFormData({ ...formData, allocated_capital: val ? Number(val) : 0 });
                                        }}
                                        className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-10 pr-4 py-3 text-sm font-bold text-white focus:border-primary/30 transition-colors font-mono"
                                        placeholder="0"
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 pt-2">
                                <Button
                                    variant="ghost"
                                    size="md"
                                    className="flex-1"
                                    type="button"
                                    onClick={() => setShowBotModal(false)}
                                    disabled={formLoading}
                                >
                                    취소
                                </Button>
                                <Button
                                    variant="primary"
                                    size="md"
                                    className="flex-1"
                                    type="submit"
                                    loading={formLoading}
                                >
                                    {modalMode === 'create' ? '생성' : '저장'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold mb-1 text-white">트레이딩 대시보드</h1>
                    <p className="text-sm text-gray-500">봇 관리 및 실시간 모니터링</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs">
                        <div className="w-1.5 h-1.5 rounded-full bg-secondary"></div>
                        <span className="font-medium text-gray-300">UPBIT 연결됨</span>
                    </div>
                    <Button variant="primary" size="sm" onClick={openCreateModal}>
                        <Plus className="w-4 h-4" />
                        새 봇 만들기
                    </Button>
                </div>
            </header>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden">
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">전체 봇</h3>
                            <Settings2 className="w-4 h-4 text-primary" />
                        </div>
                        <span className="text-xl font-bold text-white">{bots.length}개</span>
                    </div>
                </div>

                <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden">
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">가동 중</h3>
                            <Zap className="w-4 h-4 text-secondary" />
                        </div>
                        <div className="flex items-center gap-2.5">
                            {activeBotCount > 0 && (
                                <div className="w-2.5 h-2.5 rounded-full bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                            )}
                            <span className="text-xl font-bold text-white">{activeBotCount}개</span>
                        </div>
                    </div>
                </div>

                <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between relative overflow-hidden">
                    <div className="relative z-10">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">Upbit 자산</h3>
                            <Wallet className="w-4 h-4 text-primary" />
                        </div>
                        {balances.length > 0 ? (
                            <div className="space-y-1.5">
                                {balances.slice(0, 4).map((b) => (
                                    <div key={b.currency} className="flex justify-between items-center">
                                        <span className="text-xs font-medium text-gray-400">{b.currency}</span>
                                        <span className="text-xs font-bold text-white">
                                            {b.currency === 'KRW'
                                                ? `₩${Math.floor(b.total).toLocaleString()}`
                                                : b.total.toFixed(4)}
                                        </span>
                                    </div>
                                ))}
                                {balances.length > 4 && (
                                    <p className="text-[10px] text-gray-600 text-right">+{balances.length - 4}개 더</p>
                                )}
                            </div>
                        ) : (
                            <span className="text-sm text-gray-600">API 키를 등록해주세요</span>
                        )}
                    </div>
                </div>
            </div>

            {/* Bot List */}
            {bots.length === 0 ? (
                <div className="glass-panel rounded-2xl p-16 text-center">
                    <EmptyState
                        icon={<Settings2 className="w-12 h-12" />}
                        title="등록된 봇이 없습니다"
                        description="새 봇을 만들어 자동 매매를 시작하세요."
                    />
                    <div className="mt-6">
                        <Button variant="primary" size="md" onClick={openCreateModal}>
                            <Plus className="w-4 h-4" />
                            새 봇 만들기
                        </Button>
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Bot Cards */}
                    <div className="lg:col-span-4 space-y-4">
                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                            <Activity className="w-4 h-4" />
                            봇 목록
                        </h3>

                        {bots.map((bot) => {
                            const isRunning = !!botStatuses[bot.id];
                            const isSelected = selectedBotId === bot.id;
                            const isActionLoading = !!actionLoading[bot.id];

                            return (
                                <div
                                    key={bot.id}
                                    onClick={() => setSelectedBotId(bot.id)}
                                    role="button"
                                    tabIndex={0}
                                    aria-label={`${bot.symbol} 봇 선택`}
                                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedBotId(bot.id); }}
                                    className={`glass-panel p-5 rounded-2xl cursor-pointer transition-all border-2 ${
                                        isSelected
                                            ? 'border-primary/30 bg-primary/[0.03]'
                                            : 'border-transparent hover:border-white/[0.06]'
                                    }`}
                                >
                                    {/* Top row: symbol + status */}
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2.5">
                                            <div className={`w-2.5 h-2.5 rounded-full ${
                                                isRunning
                                                    ? 'bg-secondary shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                                                    : 'bg-gray-600'
                                            }`}></div>
                                            <span className="text-base font-bold text-white">{bot.symbol}</span>
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            {bot.paper_trading_mode ? (
                                                <Badge variant="info">모의투자</Badge>
                                            ) : (
                                                <Badge variant="danger">실매매</Badge>
                                            )}
                                            <Badge variant={isRunning ? 'success' : 'warning'}>
                                                {isRunning ? '가동중' : '정지'}
                                            </Badge>
                                        </div>
                                    </div>

                                    {/* Bot details */}
                                    <div className="flex items-center gap-4 text-[11px] text-gray-500 mb-4">
                                        <span>{STRATEGY_LABEL_MAP[bot.strategy_name] ?? bot.strategy_name}</span>
                                        <span>{TIMEFRAME_LABEL_MAP[bot.timeframe] ?? bot.timeframe}</span>
                                    </div>

                                    <div className="flex items-center justify-between mb-4">
                                        <div>
                                            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">운용 자본</p>
                                            <p className="text-sm font-semibold text-white font-mono">&#8361;{(bot.allocated_capital ?? 0).toLocaleString()}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">RSI / Vol MA</p>
                                            <p className="text-sm font-semibold text-white font-mono">{bot.rsi_period} / {bot.volume_ma_period}</p>
                                        </div>
                                    </div>

                                    {/* Action buttons */}
                                    <div className="flex items-center gap-2 pt-3 border-t border-white/[0.04]" onClick={(e) => e.stopPropagation()}>
                                        {isRunning ? (
                                            <Button
                                                variant="danger"
                                                size="sm"
                                                className="flex-1"
                                                onClick={() => handleStop(bot.id)}
                                                loading={isActionLoading}
                                            >
                                                <StopCircle className="w-3.5 h-3.5" />
                                                정지
                                            </Button>
                                        ) : (
                                            <>
                                                <Button
                                                    variant="primary"
                                                    size="sm"
                                                    className="flex-1"
                                                    onClick={() => handleStartClick(bot.id)}
                                                    loading={isActionLoading}
                                                >
                                                    <Play className="w-3.5 h-3.5" />
                                                    가동
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => openEditModal(bot)}
                                                    aria-label="봇 설정"
                                                >
                                                    <Edit3 className="w-3.5 h-3.5" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => setDeletingBotId(bot.id)}
                                                    aria-label="봇 삭제"
                                                    className="text-red-400 hover:text-red-300 hover:bg-red-500/[0.06]"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </Button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Timeline / Trade Logs */}
                    <div className="lg:col-span-8">
                        <div className="glass-panel p-6 rounded-2xl min-h-[500px] flex flex-col">
                            <div className="flex justify-between items-center mb-6 pb-4 border-b border-white/[0.04]">
                                <h3 className="text-base font-bold flex items-center gap-2.5">
                                    <BarChart2 className="w-5 h-5 text-secondary" />
                                    실행 타임라인
                                    {selectedBot && (
                                        <span className="text-xs text-gray-500 font-normal ml-2">
                                            {selectedBot.symbol}
                                        </span>
                                    )}
                                </h3>
                                <button
                                    aria-label="타임라인 필터"
                                    className="flex items-center gap-1.5 text-xs font-medium bg-white/[0.04] hover:bg-white/[0.08] px-3 py-2 rounded-lg border border-white/[0.06] transition-colors text-gray-400"
                                >
                                    <ListFilter className="w-3.5 h-3.5" />
                                    필터
                                </button>
                            </div>

                            <div className="space-y-3 flex-1 overflow-y-auto">
                                {tradeLogs.length > 0 ? tradeLogs.map((log) => (
                                    <div
                                        key={log.id}
                                        className={`group p-5 rounded-xl border transition-colors ${
                                            log.side === 'BUY'
                                                ? 'bg-primary/[0.03] border-primary/10 hover:border-primary/20'
                                                : 'bg-red-500/[0.03] border-red-500/10 hover:border-red-500/20'
                                        }`}
                                    >
                                        <div className="flex justify-between items-start mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className={`p-2 rounded-lg ${
                                                    log.side === 'BUY'
                                                        ? 'bg-primary/10 text-primary'
                                                        : 'bg-red-500/10 text-red-400'
                                                }`}>
                                                    {log.side === 'BUY' ? <ArrowUpRight className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                                </div>
                                                <div>
                                                    <p className={`text-sm font-bold ${log.side === 'BUY' ? 'text-primary' : 'text-red-400'}`}>
                                                        {log.side === 'BUY' ? '매수' : '매도'}
                                                    </p>
                                                    <p className="text-[10px] text-gray-500 font-medium">{log.symbol} &middot; {log.timestamp}</p>
                                                </div>
                                            </div>
                                            {log.pnl != null && (
                                                <div className="text-right">
                                                    <p className={`text-base font-bold ${log.pnl > 0 ? 'text-secondary' : 'text-red-400'}`}>
                                                        {log.pnl > 0 ? '+' : ''}&#8361;{Number(log.pnl).toLocaleString()}
                                                    </p>
                                                </div>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-6 pt-3 border-t border-white/[0.04]">
                                            <div>
                                                <p className="text-[10px] text-gray-500 mb-0.5">체결가</p>
                                                <p className="font-mono text-sm text-white font-medium">&#8361;{Number(log.price ?? 0).toLocaleString()}</p>
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
                                    <EmptyState
                                        icon={<Clock className="w-12 h-12" />}
                                        title="거래 내역이 없습니다"
                                        description={selectedBot ? '이 봇의 거래 내역이 아직 없습니다.' : '봇을 선택하면 거래 타임라인이 표시됩니다.'}
                                    />
                                )}

                                {selectedBotRunning && (
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
            )}
        </PageContainer>
    );
}
