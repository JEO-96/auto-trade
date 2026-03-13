'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { User as UserIcon, Check, Heart, MessageCircle, Mail, Calendar } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { updateNickname, getUserProfile, getPosts } from '@/lib/api/community';
import { useAuth } from '@/contexts/AuthContext';
import { formatDate } from '@/lib/utils';
import type { CommunityPost, PostType } from '@/types/community';

const POST_TYPE_BADGE: Record<PostType, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' }> = {
    backtest_share: { label: '백테스트', variant: 'info' },
    performance_share: { label: '수익률', variant: 'success' },
    strategy_review: { label: '전략 리뷰', variant: 'warning' },
    discussion: { label: '토론', variant: 'info' },
};

export default function ProfilePage() {
    const { user, refreshUser } = useAuth();
    const [nickname, setNickname] = useState('');
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState('');
    const [myPosts, setMyPosts] = useState<CommunityPost[]>([]);
    const [postCount, setPostCount] = useState(0);
    const [loadingPosts, setLoadingPosts] = useState(true);

    useEffect(() => {
        if (user?.nickname) setNickname(user.nickname);
    }, [user]);

    const fetchMyPosts = useCallback(async () => {
        if (!user) return;
        try {
            const data = await getPosts({ page: 1, page_size: 50 });
            const mine = data.posts.filter(p => p.user_id === user.id);
            setMyPosts(mine);

            const profile = await getUserProfile(user.id);
            setPostCount(profile.post_count);
        } catch (err) {
            console.error('내 게시글 로드 실패', err);
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
                        <p className="text-[10px] text-gray-500">게시글</p>
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

            {/* My Posts */}
            <div className="glass-panel rounded-2xl p-6">
                <h2 className="text-base font-bold text-white mb-4">내 커뮤니티 게시글</h2>

                {loadingPosts ? (
                    <LoadingSpinner size="sm" message="불러오는 중..." />
                ) : myPosts.length === 0 ? (
                    <div className="text-center py-8">
                        <p className="text-xs text-gray-600 mb-3">작성한 게시글이 없습니다.</p>
                        <Link href="/community">
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
                                    href={`/community/post?id=${post.id}`}
                                    className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors group"
                                >
                                    <Badge variant={badge.variant}>{badge.label}</Badge>
                                    <span className="flex-1 text-sm text-white font-medium truncate group-hover:text-primary transition-colors">
                                        {post.title}
                                    </span>
                                    <div className="flex items-center gap-3 text-[11px] text-gray-500 shrink-0">
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
        </PageContainer>
    );
}
