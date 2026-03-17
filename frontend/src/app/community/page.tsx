'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    MessageSquare, Heart, Star, TrendingUp, BarChart2,
    MessageCircle, Plus, ChevronLeft, ChevronRight, FlaskConical, LogIn
} from 'lucide-react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { getPosts, toggleLike } from '@/lib/api/community';
import { useAuth } from '@/contexts/AuthContext';
import { BOT_TIMEFRAMES, getStrategyLabel } from '@/lib/constants';
import type { CommunityPost, PostType } from '@/types/community';

const getTimeframeLabel = (value: string) => {
    const found = BOT_TIMEFRAMES.find(t => t.value === value);
    return found ? found.label : value;
};

const POST_TYPE_TABS: { label: string; value: PostType | 'all'; icon: React.ReactNode }[] = [
    { label: '전체', value: 'all', icon: <MessageSquare className="w-3.5 h-3.5" /> },
    { label: '백테스트', value: 'backtest_share', icon: <BarChart2 className="w-3.5 h-3.5" /> },
    { label: '수익률', value: 'performance_share', icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { label: '전략 리뷰', value: 'strategy_review', icon: <Star className="w-3.5 h-3.5" /> },
    { label: '자유 토론', value: 'discussion', icon: <MessageCircle className="w-3.5 h-3.5" /> },
];

const POST_TYPE_BADGE: Record<PostType, { label: string; variant: 'success' | 'warning' | 'danger' | 'info' }> = {
    backtest_share: { label: '백테스트', variant: 'info' },
    performance_share: { label: '수익률', variant: 'success' },
    strategy_review: { label: '전략 리뷰', variant: 'warning' },
    discussion: { label: '토론', variant: 'info' },
};

function StarRating({ rating }: { rating: number }) {
    return (
        <div className="flex items-center gap-0.5">
            {[1, 2, 3, 4, 5].map((i) => (
                <Star
                    key={i}
                    className={`w-3.5 h-3.5 ${i <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-500'}`}
                />
            ))}
        </div>
    );
}

function PostCard({ post, onLikeToggle, isLoggedIn, basePath }: { post: CommunityPost; onLikeToggle: (id: number) => void; isLoggedIn: boolean; basePath: string }) {
    const badge = POST_TYPE_BADGE[post.post_type];
    const timeAgo = getTimeAgo(post.created_at);

    return (
        <div className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                        <Badge variant={badge.variant}>{badge.label}</Badge>
                        {post.strategy_name && (
                            <span className="text-[10px] text-gray-500 font-medium">
                                {getStrategyLabel(post.strategy_name)}
                            </span>
                        )}
                        {post.timeframe && (
                            <span className="text-[10px] text-gray-500 font-medium">
                                {getTimeframeLabel(post.timeframe)}
                            </span>
                        )}
                    </div>
                    <Link
                        href={`${basePath}/post?id=${post.id}`}
                        className="text-white font-bold text-sm hover:text-primary transition-colors line-clamp-1"
                    >
                        {post.title}
                    </Link>
                </div>
                {post.post_type === 'strategy_review' && post.rating && (
                    <StarRating rating={post.rating} />
                )}
            </div>

            {post.content && (
                <p className="text-xs text-gray-400 leading-relaxed line-clamp-2">{post.content}</p>
            )}

            {post.post_type === 'backtest_share' && post.backtest_data && (
                <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.04] space-y-2">
                    <div className="grid grid-cols-3 gap-3">
                        <MetricItem
                            label="수익률"
                            value={`${(((Number(post.backtest_data.final_capital) - Number(post.backtest_data.initial_capital)) / Number(post.backtest_data.initial_capital)) * 100).toFixed(1)}%`}
                            positive={(Number(post.backtest_data.final_capital) - Number(post.backtest_data.initial_capital)) > 0}
                        />
                        <MetricItem label="거래 수" value={String(post.backtest_data.total_trades ?? '-')} />
                        <MetricItem label="전략" value={post.backtest_data.strategy_name ? getStrategyLabel(String(post.backtest_data.strategy_name)) : '-'} />
                    </div>
                    {(post.backtest_data.start_date || post.backtest_data.timeframe || post.backtest_data.commission_rate != null) && (
                        <div className="flex items-center gap-3 text-[10px] text-gray-500 flex-wrap">
                            {post.backtest_data.start_date && post.backtest_data.end_date && (
                                <span>{String(post.backtest_data.start_date)} ~ {String(post.backtest_data.end_date)}</span>
                            )}
                            {post.backtest_data.timeframe && (
                                <span>{getTimeframeLabel(String(post.backtest_data.timeframe))}</span>
                            )}
                            {post.backtest_data.commission_rate != null && (
                                <span>수수료 {(Number(post.backtest_data.commission_rate) * 100).toFixed(2)}%</span>
                            )}
                        </div>
                    )}
                </div>
            )}

            {post.post_type === 'performance_share' && post.performance_data && (
                <div className="grid grid-cols-3 gap-3 p-3 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                    <MetricItem
                        label="총 PnL"
                        value={`₩${Number(post.performance_data.total_pnl).toLocaleString()}`}
                        positive={post.performance_data.total_pnl > 0}
                    />
                    <MetricItem label="승률" value={`${post.performance_data.win_rate}%`} />
                    <MetricItem label={post.performance_data.is_paper ? '모의투자' : '실투자'} value={post.performance_data.symbol} />
                </div>
            )}

            <div className="flex items-center justify-between pt-2 border-t border-white/[0.04]">
                <div className="flex items-center gap-3">
                    <span className="text-[11px] text-gray-500 font-medium">
                        {post.author_nickname ?? '익명'}
                    </span>
                    <span className="text-[10px] text-gray-500">{timeAgo}</span>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => isLoggedIn ? onLikeToggle(post.id) : undefined}
                        title={isLoggedIn ? undefined : '로그인이 필요합니다'}
                        className={`flex items-center gap-1 text-xs transition-colors ${
                            !isLoggedIn ? 'text-gray-500 cursor-default' :
                            post.is_liked ? 'text-red-400' : 'text-gray-500 hover:text-red-400'
                        }`}
                    >
                        <Heart className={`w-3.5 h-3.5 ${post.is_liked ? 'fill-red-400' : ''}`} />
                        {post.like_count}
                    </button>
                    <Link
                        href={`${basePath}/post?id=${post.id}`}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-primary transition-colors"
                    >
                        <MessageCircle className="w-3.5 h-3.5" />
                        {post.comment_count}
                    </Link>
                </div>
            </div>
        </div>
    );
}

function MetricItem({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
    return (
        <div className="min-w-0">
            <p className="text-[10px] text-gray-500 mb-0.5">{label}</p>
            <p className={`text-xs font-semibold ${positive === true ? 'text-secondary' : positive === false ? 'text-red-400' : 'text-white'}`}>
                {value}
            </p>
        </div>
    );
}

function getTimeAgo(dateString: string): string {
    const diff = Date.now() - new Date(dateString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return '방금 전';
    if (minutes < 60) return `${minutes}분 전`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}시간 전`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}일 전`;
    return `${Math.floor(days / 30)}개월 전`;
}

export default function PublicCommunityPage() {
    const { isAuthenticated } = useAuth();
    const pathname = usePathname();
    const basePath = pathname?.startsWith('/dashboard') ? '/dashboard/community' : '/community';
    const [posts, setPosts] = useState<CommunityPost[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<PostType | 'all'>('all');
    const pageSize = 12;

    const fetchPosts = useCallback(async () => {
        setLoading(true);
        try {
            const params: { page: number; page_size: number; post_type?: string } = {
                page,
                page_size: pageSize,
            };
            if (activeTab !== 'all') params.post_type = activeTab;
            const data = await getPosts(params);
            setPosts(data.posts);
            setTotal(data.total);
        } catch (err) {
            console.error('게시글 로드 실패', err);
        } finally {
            setLoading(false);
        }
    }, [page, activeTab]);

    useEffect(() => {
        fetchPosts();
    }, [fetchPosts]);

    const handleTabChange = (tab: PostType | 'all') => {
        setActiveTab(tab);
        setPage(1);
    };

    const handleLikeToggle = async (postId: number) => {
        if (!isAuthenticated) return;
        try {
            const result = await toggleLike(postId);
            setPosts(prev =>
                prev.map(p =>
                    p.id === postId
                        ? { ...p, is_liked: result.liked, like_count: result.like_count }
                        : p
                )
            );
        } catch (err) {
            console.error('좋아요 실패', err);
        }
    };

    const totalPages = Math.ceil(total / pageSize);

    return (
        <>
            <header className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-1">커뮤니티</h1>
                    <p className="text-sm text-gray-500">전략 공유, 백테스트 결과, 수익률을 공유하세요</p>
                </div>
                <div className="flex items-center gap-2">
                    {isAuthenticated ? (
                        <>
                            <Link href="/dashboard/community/chat">
                                <Button variant="ghost" size="sm">
                                    <MessageSquare className="w-4 h-4" />
                                    채팅
                                </Button>
                            </Link>
                            <Link href="/dashboard/community/create">
                                <Button size="sm">
                                    <Plus className="w-4 h-4" />
                                    글쓰기
                                </Button>
                            </Link>
                        </>
                    ) : (
                        <Link href="/login">
                            <Button size="sm">
                                <LogIn className="w-4 h-4" />
                                로그인하여 참여
                            </Button>
                        </Link>
                    )}
                </div>
            </header>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1.5 mb-6 overflow-x-auto pb-1">
                {POST_TYPE_TABS.map((tab) => (
                    <button
                        key={tab.value}
                        onClick={() => handleTabChange(tab.value)}
                        className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                            activeTab === tab.value
                                ? 'bg-primary/10 text-primary border border-primary/20'
                                : 'text-gray-500 hover:text-white hover:bg-white/[0.03] border border-transparent'
                        }`}
                    >
                        {tab.icon}
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Posts Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <LoadingSpinner message="게시글 불러오는 중..." />
                </div>
            ) : posts.length === 0 ? (
                <EmptyState
                    icon={<FlaskConical className="w-12 h-12" />}
                    title="아직 게시글이 없습니다"
                    description="첫 번째 글을 작성해 보세요!"
                />
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        {posts.map((post) => (
                            <PostCard
                                key={post.id}
                                post={post}
                                onLikeToggle={handleLikeToggle}
                                isLoggedIn={isAuthenticated}
                                basePath={basePath}
                            />
                        ))}
                    </div>

                    {totalPages > 1 && (
                        <div className="flex items-center justify-center gap-2">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="p-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/[0.03] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <span className="text-xs text-gray-400 font-medium px-3">
                                {page} / {totalPages}
                            </span>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="p-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/[0.03] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    )}
                </>
            )}
        </>
    );
}
