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
    Timer,
    Plus,
    Trash2,
    ToggleLeft,
    ToggleRight,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import PageContainer from '@/components/ui/PageContainer';
import { isAxiosError } from 'axios';
import {
    getUsers, getPendingUsers, approveUser, rejectUser,
    getAllTimeframeOptions, getAllowedTimeframes, addAllowedTimeframe,
    updateAllowedTimeframe, deleteAllowedTimeframe,
    type AllowedTimeframe, type TimeframeOption,
} from '@/lib/api/admin';
import type { User } from '@/types/user';

type TabFilter = 'all' | 'pending' | 'approved' | 'rejected';
type AdminSection = 'users' | 'timeframes';

export default function AdminPage() {
    const router = useRouter();
    const [users, setUsers] = useState<User[]>([]);
    const [pendingUsers, setPendingUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [forbidden, setForbidden] = useState(false);
    const [activeTab, setActiveTab] = useState<TabFilter>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [actionLoading, setActionLoading] = useState<Record<number, string>>({});
    const [refreshing, setRefreshing] = useState(false);

    // 관리자 섹션 전환
    const [activeSection, setActiveSection] = useState<AdminSection>('users');

    // 타임프레임 관리 상태
    const [allowedTimeframes, setAllowedTimeframes] = useState<AllowedTimeframe[]>([]);
    const [allTimeframeOptions, setAllTimeframeOptions] = useState<TimeframeOption[]>([]);
    const [tfLoading, setTfLoading] = useState(false);
    const [tfActionLoading, setTfActionLoading] = useState<Record<number, boolean>>({});
    const [addingTimeframe, setAddingTimeframe] = useState(false);
    const [selectedNewTf, setSelectedNewTf] = useState('');

    const fetchTimeframes = useCallback(async () => {
        setTfLoading(true);
        try {
            const [allowed, options] = await Promise.all([
                getAllowedTimeframes(),
                getAllTimeframeOptions(),
            ]);
            setAllowedTimeframes(allowed);
            setAllTimeframeOptions(options);
        } catch (err: unknown) {
            if (isAxiosError(err) && err.response?.status === 403) {
                setForbidden(true);
            }
        } finally {
            setTfLoading(false);
        }
    }, []);

    const fetchUsers = useCallback(async () => {
        try {
            const [allUsers, pending] = await Promise.all([
                getUsers(),
                getPendingUsers(),
            ]);
            setUsers(allUsers);
            setPendingUsers(pending);
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
        fetchTimeframes();
    }, [fetchUsers, fetchTimeframes]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await Promise.all([fetchUsers(), fetchTimeframes()]);
        setRefreshing(false);
    };

    // -------- 타임프레임 핸들러 --------
    const handleAddTimeframe = async () => {
        if (!selectedNewTf) return;
        const option = allTimeframeOptions.find(o => o.timeframe === selectedNewTf);
        if (!option) return;
        setAddingTimeframe(true);
        try {
            const maxOrder = allowedTimeframes.reduce((max, tf) => Math.max(max, tf.display_order), 0);
            const newTf = await addAllowedTimeframe({
                timeframe: option.timeframe,
                label: option.label,
                display_order: maxOrder + 1,
                is_active: true,
            });
            setAllowedTimeframes(prev => [...prev, newTf]);
            setSelectedNewTf('');
        } catch (err) {
            if (isAxiosError(err)) {
                alert(err.response?.data?.detail || '추가에 실패했습니다.');
            }
        } finally {
            setAddingTimeframe(false);
        }
    };

    const handleToggleTimeframe = async (tf: AllowedTimeframe) => {
        setTfActionLoading(prev => ({ ...prev, [tf.id]: true }));
        try {
            const updated = await updateAllowedTimeframe(tf.id, { is_active: !tf.is_active });
            setAllowedTimeframes(prev => prev.map(t => t.id === tf.id ? updated : t));
        } catch {
            alert('상태 변경에 실패했습니다.');
        } finally {
            setTfActionLoading(prev => {
                const next = { ...prev };
                delete next[tf.id];
                return next;
            });
        }
    };

    const handleDeleteTimeframe = async (tf: AllowedTimeframe) => {
        if (!confirm(`'${tf.label} (${tf.timeframe})' 타임프레임을 삭제하시겠습니까?`)) return;
        setTfActionLoading(prev => ({ ...prev, [tf.id]: true }));
        try {
            await deleteAllowedTimeframe(tf.id);
            setAllowedTimeframes(prev => prev.filter(t => t.id !== tf.id));
        } catch {
            alert('삭제에 실패했습니다.');
        } finally {
            setTfActionLoading(prev => {
                const next = { ...prev };
                delete next[tf.id];
                return next;
            });
        }
    };

    // 이미 등록된 타임프레임 제외한 추가 가능 목록
    const availableToAdd = allTimeframeOptions.filter(
        o => !allowedTimeframes.some(a => a.timeframe === o.timeframe)
    );

    const handleApprove = async (userId: number) => {
        setActionLoading(prev => ({ ...prev, [userId]: 'approve' }));
        try {
            await approveUser(userId);
            setUsers(prev =>
                prev.map(u => u.id === userId ? { ...u, is_active: true } : u)
            );
            setPendingUsers(prev => prev.filter(u => u.id !== userId));
        } catch {
            alert('승인 처리에 실패했습니다.');
        } finally {
            setActionLoading(prev => {
                const next = { ...prev };
                delete next[userId];
                return next;
            });
        }
    };

    const handleReject = async (userId: number) => {
        if (!confirm('이 사용자를 거부하시겠습니까?')) return;
        setActionLoading(prev => ({ ...prev, [userId]: 'reject' }));
        try {
            await rejectUser(userId);
            setUsers(prev =>
                prev.map(u => u.id === userId ? { ...u, is_active: false } : u)
            );
            setPendingUsers(prev => prev.filter(u => u.id !== userId));
        } catch {
            alert('거부 처리에 실패했습니다.');
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
                    <h2 className="text-xl font-bold text-white mb-2">접근 권한이 없습니다</h2>
                    <p className="text-sm text-gray-500 mb-6">
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

    const formatDate = (dateStr: string) => {
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <PageContainer>
            {/* Header */}
            <header className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold mb-1 text-white flex items-center gap-2.5">
                        <Shield className="w-6 h-6 text-primary" />
                        관리자 패널
                    </h1>
                    <p className="text-sm text-gray-500">사용자 및 시스템 설정을 관리합니다.</p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06] text-sm text-gray-300 hover:bg-white/[0.08] transition-colors disabled:opacity-50"
                    aria-label="새로고침"
                >
                    <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                    새로고침
                </button>
            </header>

            {/* Section Tabs */}
            <nav className="flex gap-1 bg-white/[0.03] p-1 rounded-lg mb-8 w-fit" role="tablist">
                <button
                    role="tab"
                    aria-selected={activeSection === 'users'}
                    onClick={() => setActiveSection('users')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                        activeSection === 'users'
                            ? 'bg-white/[0.08] text-white'
                            : 'text-gray-500 hover:text-gray-300'
                    }`}
                >
                    <Users className="w-4 h-4" />
                    사용자 관리
                </button>
                <button
                    role="tab"
                    aria-selected={activeSection === 'timeframes'}
                    onClick={() => setActiveSection('timeframes')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${
                        activeSection === 'timeframes'
                            ? 'bg-white/[0.08] text-white'
                            : 'text-gray-500 hover:text-gray-300'
                    }`}
                >
                    <Timer className="w-4 h-4" />
                    캔들 주기 설정
                </button>
            </nav>

            {/* ========== 캔들 주기 설정 섹션 ========== */}
            {activeSection === 'timeframes' && (
                <div className="space-y-6">
                    {/* 설명 */}
                    <div className="glass-panel p-5 rounded-2xl">
                        <h2 className="text-base font-bold text-white mb-2 flex items-center gap-2">
                            <Timer className="w-5 h-5 text-primary" />
                            허용 캔들 주기 관리
                        </h2>
                        <p className="text-sm text-gray-500">
                            사용자가 봇 생성 및 백테스트에서 선택할 수 있는 캔들 주기를 설정합니다.
                            비활성화된 주기는 목록에 표시되지 않습니다.
                        </p>
                    </div>

                    {/* 추가 영역 */}
                    {availableToAdd.length > 0 && (
                        <div className="glass-panel p-5 rounded-2xl">
                            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">캔들 주기 추가</h3>
                            <div className="flex items-center gap-3">
                                <select
                                    value={selectedNewTf}
                                    onChange={e => setSelectedNewTf(e.target.value)}
                                    className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white focus:border-primary/30 transition-colors"
                                >
                                    <option value="">타임프레임 선택...</option>
                                    {availableToAdd.map(o => (
                                        <option key={o.timeframe} value={o.timeframe}>
                                            {o.label} ({o.timeframe})
                                        </option>
                                    ))}
                                </select>
                                <Button
                                    variant="primary"
                                    size="md"
                                    onClick={handleAddTimeframe}
                                    disabled={!selectedNewTf || addingTimeframe}
                                    loading={addingTimeframe}
                                >
                                    <Plus className="w-4 h-4" />
                                    추가
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* 등록된 타임프레임 목록 */}
                    <div className="glass-panel rounded-2xl overflow-hidden">
                        <div className="p-5 border-b border-white/[0.04]">
                            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
                                등록된 캔들 주기 ({allowedTimeframes.length}개)
                            </h3>
                        </div>

                        {tfLoading ? (
                            <div className="p-10 flex justify-center">
                                <LoadingSpinner message="로딩 중..." />
                            </div>
                        ) : allowedTimeframes.length === 0 ? (
                            <div className="p-10 text-center">
                                <EmptyState
                                    icon={<Timer className="w-10 h-10" />}
                                    title="등록된 캔들 주기가 없습니다"
                                    description="위에서 허용할 캔들 주기를 추가해주세요."
                                />
                            </div>
                        ) : (
                            <div className="divide-y divide-white/[0.03]">
                                {allowedTimeframes.map(tf => (
                                    <div
                                        key={tf.id}
                                        className="flex items-center justify-between px-5 py-4 hover:bg-white/[0.02] transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold border ${
                                                tf.is_active
                                                    ? 'bg-primary/10 border-primary/20 text-primary'
                                                    : 'bg-white/[0.02] border-white/[0.06] text-gray-600'
                                            }`}>
                                                {tf.timeframe}
                                            </div>
                                            <div>
                                                <p className={`text-sm font-semibold ${tf.is_active ? 'text-white' : 'text-gray-600'}`}>
                                                    {tf.label}
                                                </p>
                                                <p className="text-[11px] text-gray-500">
                                                    순서: {tf.display_order}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Badge variant={tf.is_active ? 'success' : 'warning'}>
                                                {tf.is_active ? '활성' : '비활성'}
                                            </Badge>
                                            <button
                                                onClick={() => handleToggleTimeframe(tf)}
                                                disabled={!!tfActionLoading[tf.id]}
                                                className="p-2 rounded-lg hover:bg-white/[0.06] transition-colors text-gray-400 hover:text-white disabled:opacity-50"
                                                aria-label={tf.is_active ? '비활성화' : '활성화'}
                                                title={tf.is_active ? '비활성화' : '활성화'}
                                            >
                                                {tf.is_active ? (
                                                    <ToggleRight className="w-5 h-5 text-secondary" />
                                                ) : (
                                                    <ToggleLeft className="w-5 h-5 text-gray-600" />
                                                )}
                                            </button>
                                            <button
                                                onClick={() => handleDeleteTimeframe(tf)}
                                                disabled={!!tfActionLoading[tf.id]}
                                                className="p-2 rounded-lg hover:bg-red-500/[0.06] transition-colors text-gray-500 hover:text-red-400 disabled:opacity-50"
                                                aria-label="삭제"
                                                title="삭제"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ========== 사용자 관리 섹션 ========== */}
            {activeSection === 'users' && <>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">전체 사용자</h3>
                        <Users className="w-4 h-4 text-white/20" />
                    </div>
                    <p className="text-2xl font-bold text-white">{users.length}</p>
                </div>
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">승인 대기</h3>
                        <Clock className="w-4 h-4 text-amber-400/40" />
                    </div>
                    <p className="text-2xl font-bold text-amber-400">{pendingCount}</p>
                </div>
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">활성 사용자</h3>
                        <UserCheck className="w-4 h-4 text-secondary/40" />
                    </div>
                    <p className="text-2xl font-bold text-secondary">
                        {users.filter(u => u.is_active).length}
                    </p>
                </div>
                <div className="glass-panel p-5 rounded-2xl">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-gray-500 text-[11px] font-semibold uppercase tracking-wider">비활성</h3>
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
                    <nav aria-label="사용자 필터 탭" className="flex gap-1 bg-white/[0.03] p-1 rounded-lg" role="tablist">
                        {tabs.map(tab => (
                            <button
                                key={tab.key}
                                role="tab"
                                aria-selected={activeTab === tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                                    activeTab === tab.key
                                        ? 'bg-white/[0.08] text-white'
                                        : 'text-gray-500 hover:text-gray-300'
                                }`}
                            >
                                {tab.label}
                                {tab.count !== undefined && (
                                    <span className={`ml-1.5 px-1.5 py-0.5 rounded text-[10px] ${
                                        activeTab === tab.key
                                            ? 'bg-primary/20 text-primary'
                                            : 'bg-white/[0.04] text-gray-500'
                                    }`}>
                                        {tab.count}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>

                    {/* Search */}
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                        <input
                            type="text"
                            placeholder="이름, 이메일, ID 검색..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 bg-white/[0.03] border border-white/[0.06] rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-primary/40 transition-colors"
                            aria-label="사용자 검색"
                        />
                    </div>
                </div>

                {/* Desktop Table */}
                <div className="hidden md:block overflow-x-auto">
                    <table className="w-full" role="table">
                        <thead>
                            <tr className="border-b border-white/[0.04]">
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-gray-500 font-semibold uppercase tracking-wider">ID</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-gray-500 font-semibold uppercase tracking-wider">사용자</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-gray-500 font-semibold uppercase tracking-wider">이메일</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-gray-500 font-semibold uppercase tracking-wider">가입일</th>
                                <th scope="col" className="text-left px-6 py-4 text-[10px] text-gray-500 font-semibold uppercase tracking-wider">상태</th>
                                <th scope="col" className="text-right px-6 py-4 text-[10px] text-gray-500 font-semibold uppercase tracking-wider">작업</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.length > 0 ? filteredUsers.map(user => {
                                const isPending = pendingUsers.some(p => p.id === user.id);
                                const isProcessing = !!actionLoading[user.id];
                                return (
                                    <tr
                                        key={user.id}
                                        className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                                    >
                                        <td className="px-6 py-4">
                                            <span className="text-xs font-mono text-gray-500">#{user.id}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-[10px] font-bold border border-white/[0.06] text-white/80">
                                                    {user.nickname?.slice(0, 2).toUpperCase() || user.email?.slice(0, 2).toUpperCase() || '??'}
                                                </div>
                                                <div>
                                                    <p className="text-sm font-semibold text-white">{user.nickname || '-'}</p>
                                                    {user.is_admin && (
                                                        <span className="text-[9px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded">ADMIN</span>
                                                    )}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-sm text-gray-400">{user.email}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-xs text-gray-500">{formatDate(user.created_at ?? '')}</span>
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
                                className="p-4 bg-white/[0.02] rounded-xl border border-white/[0.04]"
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-xs font-bold border border-white/[0.06] text-white/80">
                                            {user.nickname?.slice(0, 2).toUpperCase() || user.email?.slice(0, 2).toUpperCase() || '??'}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-white">{user.nickname || '-'}</p>
                                            <p className="text-[11px] text-gray-500">{user.email}</p>
                                        </div>
                                    </div>
                                    {getStatusBadge(user)}
                                </div>

                                <div className="flex items-center gap-4 text-[11px] text-gray-500 mb-3">
                                    <span>ID: #{user.id}</span>
                                    <span>가입: {formatDate(user.created_at ?? '')}</span>
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

            </>}
        </PageContainer>
    );
}
