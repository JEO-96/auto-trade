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
import { BOT_POLL_INTERVAL_MS, BOT_STATUS } from '@/lib/constants';
import {
    getBotList, getBotStatus, getBotLogs, startBot, stopBot,
    createBot, updateBot, deleteBot,
} from '@/lib/api/bot';
import { getKeys, getUpbitBalance, type BalanceItem } from '@/lib/api/keys';
import { getBacktestHistory } from '@/lib/api/backtest';
import { getBacktestSettings } from '@/lib/api/settings';
import { useStrategies } from '@/lib/useStrategies';
import { getErrorMessage } from '@/lib/utils';
import type { BotConfig, TradeLog } from '@/types/bot';

type ModalMode = 'create' | 'edit';


const defaultFormState: BotFormData = {
    symbols: ['BTC/KRW'],
    timeframe: '1h',
    strategy_name: 'momentum_breakout_pro_stable',
    paper_trading_mode: true,
    allocated_capital: 1000000,
};

export default function DashboardPage() {
    const toast = useToast();
    const { botStrategies } = useStrategies();

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

    // 전략별 허용 타임프레임 설정
    const [strategyTimeframeMap, setStrategyTimeframeMap] = useState<Record<string, string[]>>({});

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
        getBacktestSettings()
            .then(s => setStrategyTimeframeMap(s.strategy_timeframes))
            .catch(() => {});
        // Onboarding: check keys & backtest history
        getKeys()
            .then(keys => setHasKeys(keys.length > 0))
            .catch(() => {});
        getBacktestHistory(1, 1)
            .then(history => setHasBacktests(history.length > 0))
            .catch(() => {});
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
                    strategy_name: formData.strategy_name,
                    paper_trading_mode: formData.paper_trading_mode,
                    allocated_capital: formData.allocated_capital,
                });
            } else if (editingBotId !== null) {
                await updateBot(editingBotId, {
                    symbol: symbolStr,
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

    // 업비트 보유 KRW 현금 잔고
    const availableKrw = balances.find((b) => b.currency === 'KRW')?.free;

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
                strategyTimeframeMap={strategyTimeframeMap}
                strategies={botStrategies}
                onSubmit={handleFormSubmit}
                onClose={() => setShowBotModal(false)}
                onFormChange={setFormData}
            />

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

            {/* Onboarding Guide */}
            <OnboardingGuide
                hasKeys={hasKeys}
                hasBacktests={hasBacktests}
                hasBots={bots.length > 0}
            />

            {/* Summary Stats */}
            <SummaryStats
                botCount={bots.length}
                activeBotCount={activeBotCount}
                balances={balances}
                onAssetDetailClick={() => setShowAssetDetail(true)}
            />

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

                        {bots.map((bot) => (
                            <BotCard
                                key={bot.id}
                                bot={bot}
                                isRunning={!!botStatuses[bot.id]}
                                isSelected={selectedBotId === bot.id}
                                isActionLoading={!!actionLoading[bot.id]}
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
