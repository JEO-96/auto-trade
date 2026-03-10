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
} from 'lucide-react';
import api from '@/lib/api';

interface User {
    id: number;
    email: string;
    nickname: string;
    is_active: boolean;
    is_admin: boolean;
    created_at: string;
}

type TabFilter = 'all' | 'pending' | 'approved' | 'rejected';

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

    const fetchUsers = useCallback(async () => {
        try {
            const [allRes, pendingRes] = await Promise.all([
                api.get('/admin/users'),
                api.get('/admin/users/pending'),
            ]);
            setUsers(allRes.data);
            setPendingUsers(pendingRes.data);
        } catch (err: any) {
            if (err.response?.status === 403) {
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
            await api.post(`/admin/users/${userId}/approve`);
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
            await api.post(`/admin/users/${userId}/reject`);
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
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 text-[10px] font-semibold">
                    <Clock className="w-3 h-3" />
                    대기중
                </span>
            );
        }
        if (user.is_active) {
            return (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/10 text-secondary text-[10px] font-semibold">
                    <CheckCircle2 className="w-3 h-3" />
                    승인됨
                </span>
            );
        }
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 text-[10px] font-semibold">
                <XCircle className="w-3 h-3" />
                거부됨
            </span>
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
                    u.nickname.toLowerCase().includes(q) ||
                    String(u.id).includes(q)
            );
        }
        return list;
    })();

    const pendingCount = pendingUsers.length;

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[80vh]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
                    <p className="text-gray-500 text-sm font-medium">사용자 데이터 불러오는 중...</p>
                </div>
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
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="px-6 py-2.5 bg-primary hover:bg-primary-dark text-white rounded-xl font-semibold text-sm transition-colors"
                    >
                        대시보드로 돌아가기
                    </button>
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
        <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in-up">
            {/* Header */}
            <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold mb-1 text-white flex items-center gap-2.5">
                        <Shield className="w-6 h-6 text-primary" />
                        사용자 관리
                    </h1>
                    <p className="text-sm text-gray-500">등록된 사용자를 관리하고 가입 승인을 처리합니다.</p>
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
                                            <span className="text-xs text-gray-500">{formatDate(user.created_at)}</span>
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
                                        <Users className="w-10 h-10 mx-auto mb-3 text-gray-700" />
                                        <p className="text-sm font-semibold text-gray-400">
                                            {searchQuery ? '검색 결과가 없습니다' : '사용자가 없습니다'}
                                        </p>
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
                                    <span>가입: {formatDate(user.created_at)}</span>
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
                            <Users className="w-10 h-10 mx-auto mb-3 text-gray-700" />
                            <p className="text-sm font-semibold text-gray-400">
                                {searchQuery ? '검색 결과가 없습니다' : '사용자가 없습니다'}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
