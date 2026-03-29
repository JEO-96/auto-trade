'use client';
import { useState, useEffect, useCallback } from 'react';
import { Activity, Settings2, Plus } from 'lucide-react';
import OnboardingGuide from '@/components/OnboardingGuide';
import RiskDisclaimerModal from '@/components/RiskDisclaimerModal';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import PageContainer from '@/components/ui/PageContainer';
import { useToast } from '@/components/ui/Toast';
import BotCard from '@/components/cards/BotCard';
import TradeLogTimeline from '@/components/sections/TradeLogTimeline';
import BotFormModal from '@/components/modals/BotFormModal';
import type { BotFormData } from '@/components/modals/BotFormModal';
import DeleteConfirmationModal from '@/components/modals/DeleteConfirmationModal';
import SummaryStats from '@/components/sections/SummaryStats';
import AssetDetailModal from '@/components/modals/AssetDetailModal';
import { useAuth } from '@/contexts/AuthContext';
import { BOT_POLL_INTERVAL_MS, BOT_STATUS, getStrategyTimeframe } from '@/lib/constants';
import {
    getBotList, getBotStatus, getBotLogs, startBot, stopBot,
    createBot, updateBot, deleteBot,
} from '@/lib/api/bot';
import { getKeys, getUpbitBalance, type BalanceItem } from '@/lib/api/keys';
import { getBacktestHistory } from '@/lib/api/backtest';
import { useStrategies } from '@/lib/useStrategies';
import { useMarkets } from '@/lib/useMarkets';
import { getErrorMessage } from '@/lib/utils';
import type { BotConfig, TradeLog } from '@/types/bot';

type ModalMode = 'create' | 'edit';

const DEFAULT_STRATEGY = 'momentum_stable_1h';
const defaultFormState: BotFormData = {
    symbols: ['BTC/KRW'],
    timeframe: getStrategyTimeframe(DEFAULT_STRATEGY),
    exchange_name: 'upbit',
    strategy_name: DEFAULT_STRATEGY,
    paper_trading_mode: true,
    allocated_capital: 1000000,
};

export default function DashboardPage() {
    const toast = useToast();
    const { user } = useAuth();
    const { botStrategies } = useStrategies();
    const { symbols: availableSymbols } = useMarkets();

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
    const [formData, setFormData] = useState<BotFormData>({ ...defaultFormState });
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    // Delete confirm
    const [deletingBotId, setDeletingBotId] = useState<number | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Action loading per bot
    const [actionLoading, setActionLoading] = useState<Record<number, boolean>>({});

    // Upbit balance
    const [balances, setBalances] = useState<BalanceItem[]>([]);

    // Asset detail modal
    const [showAssetDetail, setShowAssetDetail] = useState(false);

    // Onboarding state
    const [hasKeys, setHasKeys] = useState(false);
    const [hasBacktests, setHasBacktests] = useState(false);

    const fetchBots = useCallback(async () => {
        try {
            const list = await getBotList();
            setBots(list);

            const statuses: Record<number, boolean> = {};
            await Promise.all(
                list.map(async (bot) => {
                    try {
                        const status = await getBotStatus(bot.id);
                        statuses[bot.id] = status.bot_status === BOT_STATUS.RUNNING;
                    } catch {
                        // API 실패 시 이전 상태 유지 (unknown을 false로 잘못 표시하지 않음)
                    }
                })
            );
            setBotStatuses(prev => ({ ...prev, ...statuses }));

            if (list.length > 0) {
                setSelectedBotId((prev) => {
                    if (prev === null || !list.find((b) => b.id === prev)) {
                        return list[0].id;
                    }
                    return prev;
                });
            }
        } catch {
            // polling에서 재시도됨 — 토스트 불필요
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchLogs = useCallback(async (botId: number) => {
        try {
            const logs = await getBotLogs(botId);
            setTradeLogs(logs);
        } catch {
            // polling에서 재시도됨 — 토스트 불필요
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
        if (user?.is_admin) {
            fetchBalance();
            getKeys()
                .then(keys => setHasKeys(keys.length > 0))
                .catch(() => {});
        } else {
            setHasKeys(true); // 일반 사용자는 온보딩에서 API 키 단계 스킵
        }
        getBacktestHistory(1, 1)
            .then(history => setHasBacktests(history.length > 0))
            .catch(() => {});
    }, [fetchBots, fetchBalance, user?.is_admin]);

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
            toast.error(getErrorMessage(err, '서버 연결에 실패했거나 권한이 없습니다.'));
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
            toast.error(getErrorMessage(err, '서버 연결에 실패했거나 권한이 없습니다.'));
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
            symbols: bot.symbol.split(',').map(s => s.trim()).filter(Boolean),
            timeframe: getStrategyTimeframe(bot.strategy_name),
            exchange_name: bot.exchange_name || 'upbit',
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
            if (formData.symbols.length === 0) {
                setFormError('심볼을 1개 이상 선택해주세요.');
                setFormLoading(false);
                return;
            }
            const symbolStr = formData.symbols.join(',');
            if (modalMode === 'create') {
                await createBot({
                    symbol: symbolStr,
                    timeframe: formData.timeframe,
                    exchange_name: formData.exchange_name,
                    strategy_name: formData.strategy_name,
                    paper_trading_mode: formData.paper_trading_mode,
                    allocated_capital: formData.allocated_capital,
                    ...(formData.custom_strategy_id ? { custom_strategy_id: formData.custom_strategy_id } : {}),
                });
            } else if (editingBotId !== null) {
                await updateBot(editingBotId, {
                    symbol: symbolStr,
                    timeframe: formData.timeframe,
                    exchange_name: formData.exchange_name,
                    strategy_name: formData.strategy_name,
                    paper_trading_mode: formData.paper_trading_mode,
                    allocated_capital: formData.allocated_capital,
                    ...(formData.custom_strategy_id ? { custom_strategy_id: formData.custom_strategy_id } : {}),
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
            toast.error(getErrorMessage(err, '봇 삭제에 실패했습니다.'));
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

    // 일반 사용자 봇 1개 제한
    const isAdmin = !!user?.is_admin;
    const botLimitReached = !isAdmin && bots.length >= 1;

    // 업비트 보유 KRW 현금 잔고
    const availableKrw = balances.find((b) => b.currency === 'KRW')?.free;

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[80vh]">
                <LoadingSpinner message="봇 현황을 확인하고 있어요" />
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
            <DeleteConfirmationModal
                isOpen={deletingBotId !== null}
                title="봇 삭제"
                message="이 봇을 삭제하시겠습니까? 삭제된 봇은 복구할 수 없습니다."
                onConfirm={() => deletingBotId !== null && handleDelete(deletingBotId)}
                onCancel={() => setDeletingBotId(null)}
                loading={deleteLoading}
            />

            {/* Create/Edit Bot Modal */}
            <BotFormModal
                isOpen={showBotModal}
                mode={modalMode}
                formData={formData}
                formError={formError}
                formLoading={formLoading}
                liveBotLimitReached={liveBotLimitReached}
                availableKrw={availableKrw}
                strategies={botStrategies}
                availableSymbols={availableSymbols}
                isAdmin={!!user?.is_admin}
                onSubmit={handleFormSubmit}
                onClose={() => setShowBotModal(false)}
                onFormChange={setFormData}
            />

            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold mb-1 text-th-text">트레이딩 대시보드</h1>
                    <p className="text-sm text-th-text-muted">봇 관리 및 실시간 모니터링</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-th-card border border-th-border text-xs">
                        <div className="w-1.5 h-1.5 rounded-full bg-secondary animate-live-dot"></div>
                        <span className="font-medium text-th-text-secondary">UPBIT 연결됨</span>
                    </div>
                    <Button variant="primary" size="sm" onClick={openCreateModal} disabled={botLimitReached}>
                        <Plus className="w-4 h-4" />
                        새 봇 만들기
                    </Button>
                </div>
            </header>

            {/* Onboarding Guide */}
            <OnboardingGuide
                hasKeys={hasKeys}
                hasBacktests={hasBacktests}
                hasBots={bots.length > 0}
            />

            {/* Summary Stats — 봇이 있거나 관리자일 때만 표시 */}
            {(bots.length > 0 || isAdmin) && (
                <SummaryStats
                    botCount={bots.length}
                    activeBotCount={activeBotCount}
                    balances={balances}
                    onAssetDetailClick={() => setShowAssetDetail(true)}
                    isAdmin={isAdmin}
                />
            )}

            {/* Asset Detail Modal */}
            <AssetDetailModal
                isOpen={showAssetDetail}
                onClose={() => setShowAssetDetail(false)}
                balances={balances}
            />

            {/* Bot List */}
            {bots.length === 0 ? (
                <div className="glass-panel rounded-2xl p-16 text-center">
                    <EmptyState
                        icon={<Settings2 className="w-12 h-12" />}
                        title="아직 봇이 없어요"
                        description="첫 번째 봇을 만들고 전략이 어떻게 동작하는지 확인해 보세요."
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
                        <h3 className="text-sm font-bold text-th-text-secondary uppercase tracking-wider mb-2 flex items-center gap-2">
                            <Activity className="w-4 h-4" />
                            봇 목록
                        </h3>

                        {bots.map((bot, idx) => (
                            <BotCard
                                key={bot.id}
                                bot={bot}
                                isRunning={!!botStatuses[bot.id]}
                                isSelected={selectedBotId === bot.id}
                                isActionLoading={!!actionLoading[bot.id]}
                                index={idx}
                                onSelect={setSelectedBotId}
                                onStart={handleStartClick}
                                onStop={handleStop}
                                onEdit={openEditModal}
                                onDelete={setDeletingBotId}
                            />
                        ))}
                    </div>

                    {/* Timeline / Trade Logs */}
                    <TradeLogTimeline
                        tradeLogs={tradeLogs}
                        selectedBot={selectedBot}
                        selectedBotRunning={selectedBotRunning}
                    />
                </div>
            )}
        </PageContainer>
    );
}
