'use client';
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
    Shield,
    Users,
    UserCheck,
    UserX,
    Clock,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Search,
    RefreshCw,
    Bot,
    TrendingUp,
    Activity,
    Zap,
    Database,
    ArrowUpRight,
    ArrowDownRight,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import PageContainer from '@/components/ui/PageContainer';
import ConfirmationModal from '@/components/modals/ConfirmationModal';
import { useToast } from '@/components/ui/Toast';
import { isAxiosError } from 'axios';
import StatCard from '@/components/ui/StatCard';
import { getInitials, formatDateCompact } from '@/lib/utils';
import { getUsers, getPendingUsers, approveUser, rejectUser, getAdminDashboard } from '@/lib/api/admin';
import type { AdminDashboard } from '@/lib/api/admin';
import type { User } from '@/types/user';

type TabFilter = 'all' | 'pending' | 'approved' | 'rejected';

export default function AdminPage() {
    const router = useRouter();
    const [users, setUsers] = useState<User[]>([]);
    const [pendingUsers, setPendingUsers] = useState<User[]>([]);
    const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
    const [loading, setLoading] = useState(true);
    const [forbidden, setForbidden] = useState(false);
    const [activeTab, setActiveTab] = useState<TabFilter>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [actionLoading, setActionLoading] = useState<Record<number, string>>({});
    const [refreshing, setRefreshing] = useState(false);
    const [rejectingUserId, setRejectingUserId] = useState<number | null>(null);
    const toast = useToast();

    const fetchUsers = useCallback(async () => {
        try {
            const [allUsers, pending, dashboardData] = await Promise.all([
                getUsers(),
                getPendingUsers(),
                getAdminDashboard(),
            ]);
            setUsers(allUsers);
            setPendingUsers(pending);
            setDashboard(dashboardData);
        } catch (err: unknown) {
            if (isAxiosError(err) && err.response?.status === 403) {
                setForbidden(true);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchUsers();
        setRefreshing(false);
    };

    const handleApprove = async (userId: number) => {
        setActionLoading(prev => ({ ...prev, [userId]: 'approve' }));
        try {
            await approveUser(userId);
            setUsers(prev =>
                prev.map(u => u.id === userId ? { ...u, is_active: true } : u)
            );
            setPendingUsers(prev => prev.filter(u => u.id !== userId));
        } catch {
            toast.error('승인 처리에 실패했습니다.');
        } finally {
            setActionLoading(prev => {
                const next = { ...prev };
                delete next[userId];
                return next;
            });
        }
    };

    const handleReject = (userId: number) => {
        setRejectingUserId(userId);
    };

    const executeReject = async () => {
        if (rejectingUserId === null) return;
        const userId = rejectingUserId;
        setRejectingUserId(null);
        setActionLoading(prev => ({ ...prev, [userId]: 'reject' }));
        try {
            await rejectUser(userId);
            setUsers(prev =>
                prev.map(u => u.id === userId ? { ...u, is_active: false } : u)
            );
            setPendingUsers(prev => prev.filter(u => u.id !== userId));
        } catch {
            toast.error('거부 처리에 실패했습니다.');
        } finally {
            setActionLoading(prev => {
                const next = { ...prev };
                delete next[userId];
                return next;
            });
        }
    };

    const getStatusBadge = (user: User) => {
        const isPending = pendingUsers.some(p => p.id === user.id);
        if (isPending) {
            return (
                <Badge variant="warning">
                    <Clock className="w-3 h-3" />
                    대기중
                </Badge>
            );
        }
        if (user.is_active) {
            return (
                <Badge variant="success">
                    <CheckCircle2 className="w-3 h-3" />
                    승인됨
                </Badge>
            );
        }
        return (
            <Badge variant="danger">
                <XCircle className="w-3 h-3" />
                거부됨
            </Badge>
        );
    };

    const filteredUsers = (() => {
        let list = users;
        if (activeTab === 'pending') {
            const pendingIds = new Set(pendingUsers.map(u => u.id));
            list = users.filter(u => pendingIds.has(u.id));
        } else if (activeTab === 'approved') {
            const pendingIds = new Set(pendingUsers.map(u => u.id));
            list = users.filter(u => u.is_active && !pendingIds.has(u.id));
        } else if (activeTab === 'rejected') {
            const pendingIds = new Set(pendingUsers.map(u => u.id));
            list = users.filter(u => !u.is_active && !pendingIds.has(u.id));
        }
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            list = list.filter(
                u =>
                    u.email.toLowerCase().includes(q) ||
                    (u.nickname ?? '').toLowerCase().includes(q) ||
                    String(u.id).includes(q)
            );
        }
        return list;
    })();

    const pendingCount = pendingUsers.length;

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[80vh]">
                <LoadingSpinner message="사용자 데이터 불러오는 중..." />
            </div>
        );
    }

    if (forbidden) {
        return (
            <div className="flex items-center justify-center h-[80vh]">
                <div className="glass-panel p-10 rounded-2xl text-center max-w-md mx-auto">
                    <div className="w-16 h-16 mx-auto mb-6 bg-red-500/10 rounded-2xl flex items-center justify-center">
                        <Shield className="w-8 h-8 text-red-400" />
                    </div>
                    <h2 className="text-xl font-bold text-th-text mb-2">접근 권한이 없습니다</h2>
                    <p className="text-sm text-th-text-muted mb-6">
                        이 페이지는 관리자만 접근할 수 있습니다.
                    </p>
                    <Button
                        variant="primary"
                        size="md"
                        onClick={() => router.push('/dashboard')}
                    >
                        대시보드로 돌아가기
                    </Button>
                </div>
            </div>
        );
    }

    const tabs: { key: TabFilter; label: string; count?: number }[] = [
        { key: 'all', label: '전체', count: users.length },
        { key: 'pending', label: '대기중', count: pendingCount },
        { key: 'approved', label: '승인됨' },
        { key: 'rejected', label: '거부됨' },
    ];

    return (
        <PageContainer>
            {/* Header */}
            <header className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold mb-1 text-th-text flex items-center gap-2.5">
                        <Shield className="w-6 h-6 text-primary" />
                        관리자 패널
                    </h1>
                    <p className="text-sm text-th-text-muted">사용자 및 시스템 설정을 관리합니다.</p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-th-card border border-th-border text-sm text-th-text-secondary hover:bg-th-hover transition-colors disabled:opacity-50"
                    aria-label="새로고침"
                >
                    <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                    새로고침
                </button>
            </header>

            {/* ========== 대시보드 통계 ========== */}
            {dashboard && (
                <>
                    {/* 주요 지표 카드 */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        <StatCard
                            title="전체 사용자"
                            value={dashboard.users.total.toLocaleString()}
                            icon={<Users className="w-4 h-4" />}
                            subtitle={
                                <div className="flex items-center gap-1 text-secondary">
                                    <ArrowUpRight className="w-3.5 h-3.5" />
                                    <span className="text-xs">오늘 +{dashboard.users.new_today}</span>
                                </div>
                            }
                        />
                        <StatCard
                            title="실행중 봇"
                            value={dashboard.bots.running_now}
                            icon={<Bot className="w-4 h-4" />}
                            accentColor="from-accent/10"
                            subtitle={
                                <div className="flex items-center gap-2 text-xs text-th-text-muted">
                                    <span className="text-orange-400">실매매 {dashboard.bots.live_bots}</span>
                                    <span>·</span>
                                    <span>모의 {dashboard.bots.paper_bots}</span>
                                </div>
                            }
                        />
                        <StatCard
                            title="오늘 거래"
                            value={dashboard.trades.today_trades.toLocaleString()}
                            icon={<TrendingUp className="w-4 h-4" />}
                            accentColor="from-secondary/10"
                            subtitle={
                                <div className={`flex items-center gap-1 text-xs ${dashboard.trades.today_pnl >= 0 ? 'text-secondary' : 'text-red-400'}`}>
                                    {dashboard.trades.today_pnl >= 0
                                        ? <ArrowUpRight className="w-3.5 h-3.5" />
                                        : <ArrowDownRight className="w-3.5 h-3.5" />
                                    }
                                    <span>{dashboard.trades.today_pnl >= 0 ? '+' : ''}{dashboard.trades.today_pnl.toLocaleString()} KRW</span>
                                </div>
                            }
                        />
                    </div>

                    {/* 봇 현황 + 매출 통계 + 시스템 헬스 */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
                        {/* 봇 현황 */}
                        <div className="glass-panel p-5 rounded-2xl">
                            <div className="flex items-center gap-2 mb-4">
                                <Bot className="w-4 h-4 text-primary" />
                                <h3 className="text-sm font-semibold text-th-text">봇 현황</h3>
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted">전체 봇 설정</span>
                                    <span className="text-sm font-semibold text-th-text">{dashboard.bots.total_configs}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted">현재 실행중</span>
                                    <span className="text-sm font-semibold text-primary">{dashboard.bots.running_now}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted">실매매 봇</span>
                                    <span className="text-sm font-semibold text-orange-400">{dashboard.bots.live_bots}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted">모의투자 봇</span>
                                    <span className="text-sm font-semibold text-th-text-secondary">{dashboard.bots.paper_bots}</span>
                                </div>
                            </div>
                        </div>

                        {/* 시스템 헬스 */}
                        <div className="glass-panel p-5 rounded-2xl">
                            <div className="flex items-center gap-2 mb-4">
                                <Activity className="w-4 h-4 text-primary" />
                                <h3 className="text-sm font-semibold text-th-text">시스템 상태</h3>
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted flex items-center gap-1.5">
                                        <Database className="w-3 h-3" />
                                        DB 연결
                                    </span>
                                    {dashboard.system.db_connection_ok ? (
                                        <Badge variant="success">
                                            <Zap className="w-3 h-3" />
                                            정상
                                        </Badge>
                                    ) : (
                                        <Badge variant="danger">
                                            <XCircle className="w-3 h-3" />
                                            오류
                                        </Badge>
                                    )}
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted flex items-center gap-1.5">
                                        <Bot className="w-3 h-3" />
                                        활성 봇
                                    </span>
                                    <span className="text-sm font-semibold text-th-text">{dashboard.system.active_bot_count}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted flex items-center gap-1.5">
                                        <TrendingUp className="w-3 h-3" />
                                        총 거래
                                    </span>
                                    <span className="text-sm font-semibold text-th-text">{dashboard.trades.total_trades.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-th-text-muted flex items-center gap-1.5">
                                        <TrendingUp className="w-3 h-3" />
                                        총 손익
                                    </span>
                                    <span className={`text-sm font-semibold ${dashboard.trades.total_pnl >= 0 ? 'text-secondary' : 'text-red-400'}`}>
                                        {dashboard.trades.total_pnl >= 0 ? '+' : ''}{dashboard.trades.total_pnl.toLocaleString()} KRW
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}

            {/* ========== 사용자 관리 섹션 ========== */}

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-th-text-muted text-[11px] font-semibold uppercase tracking-wider">전체 사용자</h3>
                        <Users className="w-4 h-4 text-th-text-muted" />
                    </div>
                    <p className="text-2xl font-bold text-th-text">{users.length}</p>
                </div>
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-th-text-muted text-[11px] font-semibold uppercase tracking-wider">승인 대기</h3>
                        <Clock className="w-4 h-4 text-amber-400/40" />
                    </div>
                    <p className="text-2xl font-bold text-amber-400">{pendingCount}</p>
                </div>
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-th-text-muted text-[11px] font-semibold uppercase tracking-wider">활성 사용자</h3>
                        <UserCheck className="w-4 h-4 text-secondary/40" />
                    </div>
                    <p className="text-2xl font-bold text-secondary">
                        {users.filter(u => u.is_active).length}
                    </p>
                </div>
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-th-text-muted text-[11px] font-semibold uppercase tracking-wider">비활성</h3>
                        <UserX className="w-4 h-4 text-red-400/40" />
                    </div>
                    <p className="text-2xl font-bold text-red-400">
                        {users.filter(u => !u.is_active).length}
                    </p>
                </div>
            </div>

            {/* Pending Alert */}
            {pendingCount > 0 && (
                <div className="flex items-start gap-3 p-4 mb-6 bg-amber-500/[0.04] rounded-xl border border-amber-500/10">
                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                    <div>
                        <p className="text-sm font-semibold text-amber-400">
                            {pendingCount}명의 사용자가 승인을 기다리고 있습니다
                        </p>
                        <p className="text-xs text-amber-500/60 mt-0.5">
                            &quot;대기중&quot; 탭에서 확인하고 승인 또는 거부할 수 있습니다.
                        </p>
                    </div>
                </div>
            )}

            {/* User Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                {/* Tabs + Search */}
                <div className="p-4 md:p-6 pb-0 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    {/* Tabs */}
                    <nav aria-label="사용자 필터 탭" className="flex gap-1 bg-th-card p-1 rounded-lg" role="tablist">
                        {tabs.map(tab => (
                            <button
                                key={tab.key}
                                role="tab"
                                aria-selected={activeTab === tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                                    activeTab === tab.key
                                        ? 'bg-th-hover text-th-text'
                                        : 'text-th-text-muted hover:text-th-text-secondary'
                                }`}
                            >
                                {tab.label}
                                {tab.count !== undefined && (
                                    <span className={`ml-1.5 px-1.5 py-0.5 rounded text-[10px] ${
                                        activeTab === tab.key
                                            ? 'bg-primary/20 text-primary'
                                            : 'bg-th-card text-th-text-muted'
                                    }`}>
                                        {tab.count}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>

                    {/* Search */}
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-th-text-muted" />
                        <input
                            type="text"
                            placeholder="이름, 이메일, ID 검색..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 bg-th-card border border-th-border rounded-lg text-sm text-th-text placeholder-th-text-muted focus:outline-none focus:border-primary/40 transition-colors"
                            aria-label="사용자 검색"
                        />
                    </div>
                </div>

                {/* Desktop Table */}
                <div className="hidden md:block overflow-x-auto">
                    <table className="w-full" role="table">
                        <thead>
                            <tr className="border-b border-th-border-light">
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-th-text-muted font-semibold uppercase tracking-wider">ID</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-th-text-muted font-semibold uppercase tracking-wider">사용자</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-th-text-muted font-semibold uppercase tracking-wider">이메일</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-th-text-muted font-semibold uppercase tracking-wider">가입일</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-th-text-muted font-semibold uppercase tracking-wider">상태</th>
                                <th scope="col" className="text-right px-6 py-4 text-[10px] text-th-text-muted font-semibold uppercase tracking-wider">작업</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.length > 0 ? filteredUsers.map(user => {
                                const isPending = pendingUsers.some(p => p.id === user.id);
                                const isProcessing = !!actionLoading[user.id];
                                return (
                                    <tr
                                        key={user.id}
                                        className="border-b border-th-border-light hover:bg-th-hover transition-colors"
                                    >
                                        <td className="px-6 py-4">
                                            <span className="text-xs font-mono text-th-text-muted">#{user.id}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-[10px] font-bold border border-th-border text-th-text-secondary">
                                                    {getInitials(user.nickname ?? undefined, user.email ?? undefined)}
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-th-text">{user.nickname || '-'}</p>
                                                    {user.is_admin && (
                                                        <span className="text-[9px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded">ADMIN</span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm text-th-text-secondary">{user.email}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-xs text-th-text-muted">{formatDateCompact(user.created_at ?? '')}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            {getStatusBadge(user)}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {isPending && (
                                                <div className="flex items-center justify-end gap-2">
                                                    <button
                                                        onClick={() => handleApprove(user.id)}
                                                        disabled={isProcessing}
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-secondary/10 hover:bg-secondary/20 text-secondary border border-secondary/20 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                                        aria-label={`${user.nickname || user.email} 승인`}
                                                    >
                                                        {actionLoading[user.id] === 'approve' ? (
                                                            <div className="w-3 h-3 border border-secondary/30 border-t-secondary rounded-full animate-spin" />
                                                        ) : (
                                                            <UserCheck className="w-3.5 h-3.5" />
                                                        )}
                                                        승인
                                                    </button>
                                                    <button
                                                        onClick={() => handleReject(user.id)}
                                                        disabled={isProcessing}
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                                        aria-label={`${user.nickname || user.email} 거부`}
                                                    >
                                                        {actionLoading[user.id] === 'reject' ? (
                                                            <div className="w-3 h-3 border border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                                                        ) : (
                                                            <UserX className="w-3.5 h-3.5" />
                                                        )}
                                                        거부
                                                    </button>
                                                </div>
                                            )}
                                            {!isPending && user.is_active && !user.is_admin && (
                                                <button
                                                    onClick={() => handleReject(user.id)}
                                                    disabled={isProcessing}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500/[0.06] hover:bg-red-500/[0.12] text-red-400/70 border border-red-500/10 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                                    aria-label={`${user.nickname || user.email} 비활성화`}
                                                >
                                                    <UserX className="w-3.5 h-3.5" />
                                                    비활성화
                                                </button>
                                            )}
                                            {!isPending && !user.is_active && (
                                                <button
                                                    onClick={() => handleApprove(user.id)}
                                                    disabled={isProcessing}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-secondary/[0.06] hover:bg-secondary/[0.12] text-secondary/70 border border-secondary/10 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                                    aria-label={`${user.nickname || user.email} 활성화`}
                                                >
                                                    <UserCheck className="w-3.5 h-3.5" />
                                                    활성화
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                );
                            }) : (
                                <tr>
                                    <td colSpan={6} className="px-6 py-16 text-center">
                                        <EmptyState
                                            icon={<Users className="w-10 h-10" />}
                                            title={searchQuery ? '검색 결과가 없습니다' : '사용자가 없습니다'}
                                        />
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Mobile Cards */}
                <div className="md:hidden p-4 space-y-3">
                    {filteredUsers.length > 0 ? filteredUsers.map(user => {
                        const isPending = pendingUsers.some(p => p.id === user.id);
                        const isProcessing = !!actionLoading[user.id];
                        return (
                            <div
                                key={user.id}
                                className="p-4 bg-th-card rounded-xl border border-th-border-light"
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-xs font-bold border border-th-border text-th-text-secondary">
                                            {getInitials(user.nickname ?? undefined, user.email ?? undefined)}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-th-text">{user.nickname || '-'}</p>
                                            <p className="text-[11px] text-th-text-muted">{user.email}</p>
                                        </div>
                                    </div>
                                    {getStatusBadge(user)}
                                </div>

                                <div className="flex items-center gap-4 text-[11px] text-th-text-muted mb-3">
                                    <span>ID: #{user.id}</span>
                                    <span>가입: {formatDateCompact(user.created_at ?? '')}</span>
                                    {user.is_admin && (
                                        <span className="text-[9px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded">ADMIN</span>
                                    )}
                                </div>

                                {isPending && (
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleApprove(user.id)}
                                            disabled={isProcessing}
                                            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-secondary/10 hover:bg-secondary/20 text-secondary border border-secondary/20 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                            aria-label={`${user.nickname || user.email} 승인`}
                                        >
                                            {actionLoading[user.id] === 'approve' ? (
                                                <div className="w-3 h-3 border border-secondary/30 border-t-secondary rounded-full animate-spin" />
                                            ) : (
                                                <UserCheck className="w-3.5 h-3.5" />
                                            )}
                                            승인
                                        </button>
                                        <button
                                            onClick={() => handleReject(user.id)}
                                            disabled={isProcessing}
                                            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                            aria-label={`${user.nickname || user.email} 거부`}
                                        >
                                            {actionLoading[user.id] === 'reject' ? (
                                                <div className="w-3 h-3 border border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                                            ) : (
                                                <UserX className="w-3.5 h-3.5" />
                                            )}
                                            거부
                                        </button>
                                    </div>
                                )}
                                {!isPending && user.is_active && !user.is_admin && (
                                    <button
                                        onClick={() => handleReject(user.id)}
                                        disabled={isProcessing}
                                        className="w-full flex items-center justify-center gap-1.5 py-2 bg-red-500/[0.06] hover:bg-red-500/[0.12] text-red-400/70 border border-red-500/10 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                        aria-label={`${user.nickname || user.email} 비활성화`}
                                    >
                                        <UserX className="w-3.5 h-3.5" />
                                        비활성화
                                    </button>
                                )}
                                {!isPending && !user.is_active && (
                                    <button
                                        onClick={() => handleApprove(user.id)}
                                        disabled={isProcessing}
                                        className="w-full flex items-center justify-center gap-1.5 py-2 bg-secondary/[0.06] hover:bg-secondary/[0.12] text-secondary/70 border border-secondary/10 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                        aria-label={`${user.nickname || user.email} 활성화`}
                                    >
                                        <UserCheck className="w-3.5 h-3.5" />
                                        활성화
                                    </button>
                                )}
                            </div>
                        );
                    }) : (
                        <div className="py-12 text-center">
                            <EmptyState
                                icon={<Users className="w-10 h-10" />}
                                title={searchQuery ? '검색 결과가 없습니다' : '사용자가 없습니다'}
                            />
                        </div>
                    )}
                </div>
            </div>

            <ConfirmationModal
                isOpen={rejectingUserId !== null}
                title="사용자 거부"
                message="이 사용자를 거부/비활성화하시겠습니까?"
                confirmLabel="거부"
                variant="danger"
                onConfirm={executeReject}
                onCancel={() => setRejectingUserId(null)}
            />
        </PageContainer>
    );
}
