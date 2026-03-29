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
import type { CommunityPost, PostType } from '@/types/community';

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
            // error handled by UI state
        } finally {
            setLoadingPosts(false);
        }
    }, [user]);

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
            // error handled by UI state
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
        if (key === 'notification_interval') return; // interval은 별도 핸들러 사용
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
            <h1 className="text-2xl font-bold text-white mb-6">내 프로필</h1>

            {/* Profile Card */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-4 mb-6">
                    <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center border border-white/[0.06]">
                        <UserIcon className="w-8 h-8 text-white/60" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-white truncate">{user?.nickname || user?.email || '사용자'}</h2>
                        <div className="flex items-center gap-3 mt-1 flex-wrap min-w-0">
                            <span className="flex items-center gap-1 text-xs text-gray-500 min-w-0">
                                <Mail className="w-3 h-3 shrink-0" />
                                <span className="truncate">{user?.email}</span>
                            </span>
                            {user?.created_at && (
                                <span className="flex items-center gap-1 text-xs text-gray-500 shrink-0">
                                    <Calendar className="w-3 h-3 shrink-0" />
                                    {formatDate(user.created_at)}
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="text-center">
                        <p className="text-2xl font-bold text-white">{postCount}</p>
                        <p className="text-[10px] sm:text-xs text-gray-500">게시글</p>
                    </div>
                </div>

                {/* Nickname Form */}
                <div className="p-4 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                    <h3 className="text-sm font-semibold text-white mb-3">닉네임 변경</h3>
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
                    {saved && (
                        <p className="text-xs text-secondary mt-2 font-medium">닉네임이 변경되었습니다.</p>
                    )}
                </div>
            </div>

            {/* Telegram Settings */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Bell className="w-4 h-4 text-blue-400" />
                    <h3 className="text-sm font-semibold text-white">텔레그램 알림 설정</h3>
                    {user?.telegram_chat_id && (
                        <Badge variant="success">연동됨</Badge>
                    )}
                </div>

                {user?.telegram_chat_id ? (
                    <div className="space-y-3">
                        <div className="flex items-center gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                            <Send className="w-4 h-4 text-blue-400 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-gray-400">Chat ID</p>
                                <p className="text-sm text-white font-mono">{user.telegram_chat_id}</p>
                            </div>
                            <div className="flex gap-2 shrink-0">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleTestTelegram}
                                    loading={telegramTesting}
                                >
                                    테스트
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleUnlinkTelegram}
                                    className="text-red-400 hover:text-red-300"
                                >
                                    <Unlink className="w-3 h-3" />
                                </Button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.04] text-xs text-gray-400 space-y-2.5">
                            <p><span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-500/20 text-blue-400 text-[10px] sm:text-xs font-bold mr-1.5">1</span>텔레그램에서 <a href="https://t.me/backtested_alert_bot" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline font-medium">@backtested_alert_bot</a>을 검색하고 <span className="text-white font-medium">/start</span>를 보내세요.</p>
                            <p><span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-500/20 text-blue-400 text-[10px] sm:text-xs font-bold mr-1.5">2</span>봇이 응답하면, <span className="text-white font-medium">/chatid</span>를 입력하세요. 봇이 Chat ID를 알려줍니다.</p>
                            <p><span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-500/20 text-blue-400 text-[10px] sm:text-xs font-bold mr-1.5">3</span>받은 숫자를 아래에 입력하면 연동 완료!</p>
                        </div>
                        <form onSubmit={handleSaveTelegram} className="flex items-end gap-3">
                            <div className="flex-1">
                                <Input
                                    value={chatId}
                                    onChange={(e) => setChatId(e.target.value)}
                                    placeholder="텔레그램 Chat ID 입력"
                                    error={telegramError}
                                />
                            </div>
                            <Button type="submit" size="md" loading={telegramSaving}>
                                {telegramSaved ? <Check className="w-4 h-4" /> : <><Link2 className="w-4 h-4 mr-1" />연동</>}
                            </Button>
                        </form>
                        {telegramSaved && (
                            <p className="text-xs text-secondary font-medium">텔레그램이 연동되었습니다.</p>
                        )}
                    </div>
                )}
            </div>

            {/* Notification Settings */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Bell className="w-4 h-4 text-yellow-400" />
                    <h3 className="text-sm font-semibold text-white">알림 카테고리 설정</h3>
                    {!user?.telegram_chat_id && (
                        <span className="text-[10px] sm:text-xs text-gray-500 ml-auto">텔레그램 연동 후 사용 가능</span>
                    )}
                </div>

                <div className="space-y-2">
                    {([
                        {
                            key: 'notification_trade' as keyof NotificationSettings,
                            label: '매매 체결 알림',
                            description: '매수/매도 체결, 손익, 캔들 분석 피드백',
                            icon: <TrendingUp className="w-4 h-4 text-green-400" />,
                        },
                        {
                            key: 'notification_bot_status' as keyof NotificationSettings,
                            label: '봇 상태 알림',
                            description: '봇 시작, 종료, 자동 종료 알림',
                            icon: <Bot className="w-4 h-4 text-blue-400" />,
                        },
                        {
                            key: 'notification_system' as keyof NotificationSettings,
                            label: '시스템 알림',
                            description: '공지사항, 점검 안내 등',
                            icon: <AlertTriangle className="w-4 h-4 text-orange-400" />,
                        },
                    ]).map(({ key, label, description, icon }) => (
                        <div
                            key={key}
                            className="flex items-center gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04]"
                        >
                            <div className="shrink-0">{icon}</div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-white font-medium">{label}</p>
                                <p className="text-[11px] sm:text-xs text-gray-500">{description}</p>
                            </div>
                            <button
                                type="button"
                                disabled={!user?.telegram_chat_id || notifSaving}
                                onClick={() => handleToggleNotification(key)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed ${
                                    notifSettings[key]
                                        ? 'bg-primary'
                                        : 'bg-white/[0.03]'
                                }`}
                            >
                                <span
                                    className={`inline-block h-4 w-4 rounded-full bg-white transition-transform duration-200 ${
                                        notifSettings[key] ? 'translate-x-6' : 'translate-x-1'
                                    }`}
                                />
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Notification Interval */}
            <div className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Clock className="w-4 h-4 text-purple-400" />
                    <h3 className="text-sm font-semibold text-white">정기 분석 알림 주기</h3>
                    {!user?.telegram_chat_id && (
                        <span className="text-[10px] sm:text-xs text-gray-500 ml-auto">텔레그램 연동 후 사용 가능</span>
                    )}
                </div>
                <p className="text-[11px] sm:text-xs text-gray-500 mb-3">
                    캔들 분석 피드백의 전송 주기를 설정합니다. 매매 체결/봇 상태 알림은 항상 즉시 전송됩니다.
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {([
                        { value: 'realtime', label: '매 캔들', desc: '캔들 마감마다' },
                        { value: '4h', label: '4시간', desc: '4시간 간격' },
                        { value: '12h', label: '12시간', desc: '12시간 간격' },
                        { value: 'daily', label: '1일', desc: '하루 1회' },
                    ]).map(({ value, label, desc }) => {
                        const isSelected = notifSettings.notification_interval === value;
                        return (
                            <button
                                key={value}
                                type="button"
                                disabled={!user?.telegram_chat_id || notifSaving}
                                onClick={() => handleChangeInterval(value)}
                                className={`p-3 rounded-xl border text-center transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                                    isSelected
                                        ? 'border-primary bg-primary/10 text-primary'
                                        : 'border-white/[0.06] bg-white/[0.02] text-gray-400 hover:bg-white/[0.03]'
                                }`}
                            >
                                <p className={`text-sm font-bold ${isSelected ? 'text-primary' : 'text-white'}`}>{label}</p>
                                <p className="text-[10px] sm:text-xs text-gray-500 mt-0.5">{desc}</p>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* My Posts */}
            <div className="glass-panel rounded-2xl p-6">
                <h2 className="text-base font-bold text-white mb-4">내 커뮤니티 게시글</h2>

                {loadingPosts ? (
                    <LoadingSpinner size="sm" message="불러오는 중..." />
                ) : myPosts.length === 0 ? (
                    <div className="text-center py-8">
                        <p className="text-xs text-gray-500 mb-3">작성한 게시글이 없습니다.</p>
                        <Link href="/dashboard/community">
                            <Button variant="ghost" size="sm">커뮤니티 바로가기</Button>
                        </Link>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {myPosts.map((post) => {
                            const badge = POST_TYPE_BADGE[post.post_type];
                            return (
                                <Link
                                    key={post.id}
                                    href={`/dashboard/community/post?id=${post.id}`}
                                    className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.03] transition-colors group"
                                >
                                    <Badge variant={badge.variant}>{badge.label}</Badge>
                                    <span className="flex-1 text-sm text-white font-medium truncate group-hover:text-primary transition-colors">
                                        {post.title}
                                    </span>
                                    <div className="flex items-center gap-3 text-[11px] sm:text-xs text-gray-500 shrink-0">
                                        <span className="flex items-center gap-0.5">
                                            <Heart className="w-3 h-3" /> {post.like_count}
                                        </span>
                                        <span className="flex items-center gap-0.5">
                                            <MessageCircle className="w-3 h-3" /> {post.comment_count}
                                        </span>
                                    </div>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* 회원 탈퇴 */}
            <div className="mt-10 p-6 bg-red-500/[0.03] border border-red-500/10 rounded-2xl">
                <h3 className="text-sm font-semibold text-red-400 mb-2">회원 탈퇴</h3>
                <p className="text-xs text-gray-500 mb-4">
                    탈퇴 시 모든 데이터(봇, 거래 기록, API 키 등)가 영구 삭제됩니다. 이 작업은 되돌릴 수 없습니다.
                </p>
                <Button
                    variant="ghost"
                    size="sm"
                    className="!text-red-400 hover:!bg-red-500/10"
                    onClick={() => setShowWithdrawModal(true)}
                >
                    회원 탈퇴
                </Button>
            </div>

            <DeleteConfirmationModal
                isOpen={showWithdrawModal}
                title="회원 탈퇴"
                message="정말로 탈퇴하시겠습니까? 모든 데이터가 영구 삭제되며 복구할 수 없습니다."
                loading={withdrawLoading}
                onConfirm={async () => {
                    setWithdrawLoading(true);
                    try {
                        await withdrawAccount();
                        toast.success('회원 탈퇴가 완료되었습니다.');
                        logout();
                    } catch {
                        toast.error('탈퇴 처리에 실패했습니다.');
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
