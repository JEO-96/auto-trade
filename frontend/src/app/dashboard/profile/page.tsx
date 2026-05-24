'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { User as UserIcon, Check, Heart, MessageCircle, Mail, Calendar, Send, Link2, Unlink, Bell, TrendingUp, Bot, AlertTriangle, Clock } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { useToast } from '@/components/ui/Toast';
import { updateNickname, getUserProfile, getPosts, linkTelegram, unlinkTelegram, testTelegramNotification } from '@/lib/api/community';
import { updateNotificationSettings, withdrawAccount } from '@/lib/api/auth';
import DeleteConfirmationModal from '@/components/modals/DeleteConfirmationModal';
import { useAuth } from '@/contexts/AuthContext';
import type { NotificationSettings } from '@/types/user';
import { formatDate } from '@/lib/utils';
import { POST_TYPE_BADGE } from '@/lib/constants';
import type { CommunityPost } from '@/types/community';

export default function ProfilePage() {
    const { user, refreshUser, logout } = useAuth();
    const toast = useToast();
    const [nickname, setNickname] = useState('');
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState('');
    const [showWithdrawModal, setShowWithdrawModal] = useState(false);
    const [withdrawLoading, setWithdrawLoading] = useState(false);
    const [myPosts, setMyPosts] = useState<CommunityPost[]>([]);
    const [postCount, setPostCount] = useState(0);
    const [loadingPosts, setLoadingPosts] = useState(true);

    // Telegram
    const [chatId, setChatId] = useState('');
    const [telegramSaving, setTelegramSaving] = useState(false);
    const [telegramSaved, setTelegramSaved] = useState(false);
    const [telegramError, setTelegramError] = useState('');
    const [telegramTesting, setTelegramTesting] = useState(false);

    // Notification Settings
    const [notifSettings, setNotifSettings] = useState<NotificationSettings>({
        notification_trade: true,
        notification_bot_status: true,
        notification_system: true,
        notification_stock_alert: false,
        notification_pnl_summary: true,
        notification_interval: 'realtime',
    });
    const [notifSaving, setNotifSaving] = useState(false);

    useEffect(() => {
        if (user?.nickname) setNickname(user.nickname);
        if (user?.telegram_chat_id) setChatId(user.telegram_chat_id);
        // 알림 설정은 user 객체에서 초기화
        if (user) {
            setNotifSettings({
                notification_trade: user.notification_trade ?? true,
                notification_bot_status: user.notification_bot_status ?? true,
                notification_system: user.notification_system ?? true,
                notification_stock_alert: user.notification_stock_alert ?? false,
                notification_pnl_summary: user.notification_pnl_summary ?? true,
                notification_interval: user.notification_interval ?? 'realtime',
            });
        }
    }, [user]);

    const fetchMyPosts = useCallback(async () => {
        if (!user) return;
        try {
            const data = await getPosts({ page: 1, page_size: 50 });
            const mine = data.posts.filter(p => p.user_id === user.id);
            setMyPosts(mine);

            const profile = await getUserProfile(user.id);
            setPostCount(profile.post_count);
        } catch {
            toast.error('게시글을 불러오지 못했습니다.');
        } finally {
            setLoadingPosts(false);
        }
    }, [user, toast]);

    useEffect(() => {
        fetchMyPosts();
    }, [fetchMyPosts]);

    const handleSaveNickname = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSaved(false);

        const trimmed = nickname.trim();
        if (trimmed.length < 2 || trimmed.length > 20) {
            setError('닉네임은 2~20자여야 합니다.');
            return;
        }

        setSaving(true);
        try {
            await updateNickname(trimmed);
            await refreshUser();
            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '닉네임 변경에 실패했습니다.';
            setError(msg);
        } finally {
            setSaving(false);
        }
    };

    const handleSaveTelegram = async (e: React.FormEvent) => {
        e.preventDefault();
        setTelegramError('');
        setTelegramSaved(false);

        const trimmed = chatId.trim();
        if (!trimmed || !trimmed.replace('-', '').match(/^\d+$/)) {
            setTelegramError('숫자로 된 Chat ID를 입력해주세요.');
            return;
        }

        setTelegramSaving(true);
        try {
            await linkTelegram(trimmed);
            await refreshUser();
            setTelegramSaved(true);
            setTimeout(() => setTelegramSaved(false), 3000);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '텔레그램 연동에 실패했습니다.';
            setTelegramError(msg);
        } finally {
            setTelegramSaving(false);
        }
    };

    const handleUnlinkTelegram = async () => {
        try {
            await unlinkTelegram();
            setChatId('');
            await refreshUser();
        } catch {
            toast.error('텔레그램 연동 해제에 실패했습니다.');
        }
    };

    const handleTestTelegram = async () => {
        setTelegramTesting(true);
        try {
            await testTelegramNotification();
            toast.success('텔레그램으로 테스트 메시지를 전송했습니다!');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '테스트 메시지 전송에 실패했습니다.';
            toast.error(msg);
        } finally {
            setTelegramTesting(false);
        }
    };

    const handleToggleNotification = async (key: keyof NotificationSettings) => {
        if (key === 'notification_interval') return;
        const updated = { ...notifSettings, [key]: !notifSettings[key] };
        setNotifSettings(updated);
        setNotifSaving(true);
        try {
            await updateNotificationSettings(updated);
            await refreshUser();
        } catch (err: unknown) {
            setNotifSettings(notifSettings);
            const msg = err instanceof Error ? err.message : '알림 설정 변경에 실패했습니다.';
            toast.error(msg);
        } finally {
            setNotifSaving(false);
        }
    };

    const handleChangeInterval = async (interval: string) => {
        const updated = { ...notifSettings, notification_interval: interval };
        setNotifSettings(updated);
        setNotifSaving(true);
        try {
            await updateNotificationSettings(updated);
            await refreshUser();
        } catch (err: unknown) {
            setNotifSettings(notifSettings);
            const msg = err instanceof Error ? err.message : '알림 주기 변경에 실패했습니다.';
            toast.error(msg);
        } finally {
            setNotifSaving(false);
        }
    };

    return (
        <PageContainer maxWidth="max-w-3xl">
            <h1 className="text-2xl font-bold text-th-text mb-6">내 프로필</h1>

            {/* Profile Card */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-4 mb-6">
                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center border border-th-border">
                        <UserIcon className="w-8 h-8 text-th-text/60" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-th-text truncate">{user?.nickname || user?.email || '사용자'}</h2>
                        <div className="flex items-center gap-3 mt-1 flex-wrap min-w-0">
                            <span className="flex items-center gap-1 text-xs text-th-text-muted min-w-0">
                                <Mail className="w-3 h-3 shrink-0" />
                                <span className="truncate">{user?.email}</span>
                            </span>
                            {user?.created_at && (
                                <span className="flex items-center gap-1 text-xs text-th-text-muted shrink-0">
                                    <Calendar className="w-3 h-3 shrink-0" />
                                    {formatDate(user.created_at)}
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="text-center">
                        <p className="text-2xl font-bold text-th-text">{postCount}</p>
                        <p className="text-[10px] sm:text-xs text-th-text-muted">게시글</p>
                    </div>
                </div>

                <div className="p-4 bg-th-card rounded-xl border border-th-border-light">
                    <h3 className="text-sm font-semibold text-th-text mb-3">닉네임 변경</h3>
                    <form onSubmit={handleSaveNickname} className="flex items-end gap-3">
                        <div className="flex-1">
                            <Input
                                value={nickname}
                                onChange={(e) => setNickname(e.target.value)}
                                placeholder="닉네임을 입력하세요 (2~20자)"
                                maxLength={20}
                                error={error}
                            />
                        </div>
                        <Button type="submit" size="md" loading={saving}>
                            {saved ? <Check className="w-4 h-4" /> : '저장'}
                        </Button>
                    </form>
                </div>
            </div>

            {/* Telegram Settings */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Bell className="w-4 h-4 text-blue-400" />
                    <h3 className="text-sm font-semibold text-th-text">텔레그램 알림 설정</h3>
                    {user?.telegram_chat_id && <Badge variant="success">연동됨</Badge>}
                </div>
                {user?.telegram_chat_id ? (
                    <div className="space-y-3">
                        <div className="flex items-center gap-3 p-3 bg-th-card rounded-xl border border-th-border-light">
                            <Send className="w-4 h-4 text-blue-400 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-th-text-secondary">Chat ID</p>
                                <p className="text-sm text-th-text font-mono">{user.telegram_chat_id}</p>
                            </div>
                            <div className="flex gap-2 shrink-0">
                                <Button variant="ghost" size="sm" onClick={handleTestTelegram} loading={telegramTesting}>테스트</Button>
                                <Button variant="ghost" size="sm" onClick={handleUnlinkTelegram} className="text-red-400 hover:text-red-300">
                                    <Unlink className="w-3 h-3" />
                                </Button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <div className="p-3 bg-th-card rounded-xl border border-th-border-light text-xs text-th-text-secondary space-y-2.5">
                            <p>텔레그램에서 <a href="https://t.me/backtested_alert_bot" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">@backtested_alert_bot</a>에 /start와 /chatid를 보내세요.</p>
                        </div>
                        <form onSubmit={handleSaveTelegram} className="flex items-end gap-3">
                            <div className="flex-1">
                                <Input value={chatId} onChange={(e) => setChatId(e.target.value)} placeholder="텔레그램 Chat ID 입력" error={telegramError} />
                            </div>
                            <Button type="submit" size="md" loading={telegramSaving}>{telegramSaved ? <Check className="w-4 h-4" /> : '연동'}</Button>
                        </form>
                    </div>
                )}
            </div>

            {/* Notification Settings */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Bell className="w-4 h-4 text-yellow-400" />
                    <h3 className="text-sm font-semibold text-th-text">Notification Categories</h3>
                </div>

                <div className="space-y-2">
                    {[
                        { key: 'notification_trade', label: 'Trade Alerts', description: 'BUY/SELL fills, profit/loss, and candle analysis feedback', icon: <TrendingUp className="w-4 h-4 text-green-400" /> },
                        { key: 'notification_bot_status', label: 'Bot Status', description: 'Bot start/stop and auto-shutdown alerts', icon: <Bot className="w-4 h-4 text-blue-400" /> },
                        { key: 'notification_pnl_summary', label: 'PnL Summary', description: 'Daily and weekly performance summaries', icon: <TrendingUp className="w-4 h-4 text-purple-400" /> },
                        { key: 'notification_stock_alert', label: 'Stock Alerts', description: 'Scanner candidates, entry/exit price alerts', icon: <TrendingUp className="w-4 h-4 text-accent" /> },
                        { key: 'notification_system', label: 'System Updates', description: 'Announcements and maintenance guides', icon: <AlertTriangle className="w-4 h-4 text-orange-400" /> },
                    ].map((item) => {
                        const key = item.key as keyof NotificationSettings;
                        return (
                            <div key={key} className="flex items-center gap-3 p-3 bg-th-card rounded-xl border border-th-border-light">
                                <div className="shrink-0">{item.icon}</div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-th-text font-medium">{item.label}</p>
                                    <p className="text-[11px] sm:text-xs text-th-text-muted">{item.description}</p>
                                </div>
                                <button
                                    type="button"
                                    disabled={!user?.telegram_chat_id || notifSaving}
                                    onClick={() => handleToggleNotification(key)}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${notifSettings[key] ? 'bg-primary' : 'bg-th-hover'} disabled:opacity-40`}
                                >
                                    <span className={`inline-block h-4 w-4 rounded-full bg-th-text transition-transform duration-200 ${notifSettings[key] ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Notification Interval */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Clock className="w-4 h-4 text-purple-400" />
                    <h3 className="text-sm font-semibold text-th-text">Analysis Feedback Interval</h3>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                        { value: 'realtime', label: 'Every Candle' },
                        { value: '4h', label: '4 Hours' },
                        { value: '12h', label: '12 Hours' },
                        { value: 'daily', label: 'Daily' },
                    ].map(({ value, label }) => {
                        const isSelected = notifSettings.notification_interval === value;
                        return (
                            <button
                                key={value}
                                type="button"
                                disabled={!user?.telegram_chat_id || notifSaving}
                                onClick={() => handleChangeInterval(value)}
                                className={`p-3 rounded-xl border text-center transition-all ${isSelected ? 'border-primary bg-primary/10 text-primary' : 'border-th-border bg-th-card text-th-text-secondary'} disabled:opacity-40`}
                            >
                                <p className="text-sm font-bold">{label}</p>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Withdrawal */}
            <div className="mt-10 p-6 bg-red-500/[0.03] border border-red-500/10 rounded-2xl">
                <h3 className="text-sm font-semibold text-red-400 mb-2">Delete Account</h3>
                <Button variant="ghost" size="sm" className="!text-red-400 hover:!bg-red-500/10" onClick={() => setShowWithdrawModal(true)}>Withdraw Account</Button>
            </div>

            <DeleteConfirmationModal
                isOpen={showWithdrawModal}
                title="Withdraw Account"
                message="Are you sure you want to delete your account? This cannot be undone."
                loading={withdrawLoading}
                onConfirm={async () => {
                    setWithdrawLoading(true);
                    try {
                        await withdrawAccount();
                        toast.success('Account deleted.');
                        logout();
                    } catch {
                        toast.error('Failed to withdraw.');
                    } finally {
                        setWithdrawLoading(false);
                        setShowWithdrawModal(false);
                    }
                }}
                onCancel={() => setShowWithdrawModal(false)}
            />
        </PageContainer>
    );
}
