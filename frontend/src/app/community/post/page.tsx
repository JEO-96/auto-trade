'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
    ArrowLeft, Heart, Star, MessageCircle, Trash2, Send, User as UserIcon, LogIn
} from 'lucide-react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import DeleteConfirmationModal from '@/components/modals/DeleteConfirmationModal';
import { getPost, toggleLike, getComments, createComment, deleteComment, deletePost } from '@/lib/api/community';
import { useAuth } from '@/contexts/AuthContext';
import { formatDateTime } from '@/lib/utils';
import { getStrategyLabel, POST_TYPE_BADGE, TIMEFRAME_LABEL_MAP } from '@/lib/constants';
import type { CommunityPost, PostComment, PostType } from '@/types/community';


function StarDisplay({ rating }: { rating: number }) {
    return (
        <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((i) => (
                <Star
                    key={i}
                    className={`w-5 h-5 ${i <= rating ? 'text-amber-400 fill-amber-400' : 'text-th-text-muted'}`}
                />
            ))}
            <span className="text-sm text-th-text-secondary ml-1 font-semibold">{rating}/5</span>
        </div>
    );
}

export default function PublicPostDetailPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const pathname = usePathname();
    const basePath = pathname?.startsWith('/dashboard') ? '/dashboard/community' : '/community';
    const { user, isAuthenticated } = useAuth();
    const toast = useToast();
    const postId = Number(searchParams.get('id'));

    const [post, setPost] = useState<CommunityPost | null>(null);
    const [comments, setComments] = useState<PostComment[]>([]);
    const [loading, setLoading] = useState(true);
    const [commentText, setCommentText] = useState('');
    const [submittingComment, setSubmittingComment] = useState(false);
    const [deletingCommentId, setDeletingCommentId] = useState<number | null>(null);
    const [showDeletePost, setShowDeletePost] = useState(false);

    const fetchData = useCallback(async () => {
        if (!postId) return;
        try {
            const [postData, commentsData] = await Promise.all([
                getPost(postId),
                getComments(postId),
            ]);
            setPost(postData);
            setComments(commentsData);
        } catch {
            toast.error('게시글을 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [postId, toast]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleLike = async () => {
        if (!post || !isAuthenticated) return;
        try {
            const result = await toggleLike(post.id);
            setPost(prev => prev ? { ...prev, is_liked: result.liked, like_count: result.like_count } : prev);
        } catch {
            toast.error('좋아요 처리에 실패했습니다.');
        }
    };

    const handleAddComment = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!commentText.trim() || !postId) return;
        setSubmittingComment(true);
        try {
            const newComment = await createComment(postId, commentText.trim());
            setComments(prev => [...prev, newComment]);
            setCommentText('');
            setPost(prev => prev ? { ...prev, comment_count: prev.comment_count + 1 } : prev);
        } catch {
            toast.error('댓글 작성에 실패했습니다.');
        } finally {
            setSubmittingComment(false);
        }
    };

    const handleDeleteComment = (commentId: number) => {
        setDeletingCommentId(commentId);
    };

    const executeDeleteComment = async () => {
        if (deletingCommentId === null) return;
        const commentId = deletingCommentId;
        setDeletingCommentId(null);
        try {
            await deleteComment(commentId);
            setComments(prev => prev.filter(c => c.id !== commentId));
            setPost(prev => prev ? { ...prev, comment_count: Math.max(0, prev.comment_count - 1) } : prev);
        } catch {
            toast.error('댓글 삭제에 실패했습니다.');
        }
    };

    const handleDeletePost = () => {
        if (!post) return;
        setShowDeletePost(true);
    };

    const executeDeletePost = async () => {
        if (!post) return;
        setShowDeletePost(false);
        try {
            await deletePost(post.id);
            router.push(basePath);
        } catch {
            toast.error('게시글 삭제에 실패했습니다.');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <LoadingSpinner message="게시글을 가져오고 있어요" />
            </div>
        );
    }

    if (!post) {
        return (
            <div className="max-w-3xl mx-auto">
                <p className="text-th-text-secondary text-center py-20">게시글을 찾을 수 없습니다.</p>
            </div>
        );
    }

    const badge = POST_TYPE_BADGE[post.post_type];
    const isAuthor = user?.id === post.user_id;

    return (
        <div className="max-w-3xl mx-auto">
            <Link
                href={basePath}
                className="inline-flex items-center gap-1.5 text-xs text-th-text-muted hover:text-th-text transition-colors mb-6"
            >
                <ArrowLeft className="w-3.5 h-3.5" />
                커뮤니티로 돌아가기
            </Link>

            {/* Post */}
            <article className="glass-panel rounded-2xl p-6 mb-6">
                <div className="flex items-center gap-2 mb-3">
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                    {post.strategy_name && (
                        <span className="text-[11px] sm:text-xs text-th-text-muted font-medium">{getStrategyLabel(post.strategy_name)}</span>
                    )}
                    {post.timeframe && (
                        <span className="text-[11px] sm:text-xs text-th-text-muted font-medium">{TIMEFRAME_LABEL_MAP[post.timeframe] || post.timeframe}</span>
                    )}
                </div>

                <h1 className="text-xl font-bold text-th-text mb-3">{post.title}</h1>

                {post.post_type === 'strategy_review' && post.rating && (
                    <div className="mb-4">
                        <StarDisplay rating={post.rating} />
                    </div>
                )}

                <div className="flex items-center gap-3 mb-5 pb-4 border-b border-th-border-light">
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center border border-th-border">
                        <UserIcon className="w-3.5 h-3.5 text-th-text/60" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-th-text">{post.author_nickname ?? '익명'}</p>
                        <p className="text-[10px] sm:text-xs text-th-text-muted">{formatDateTime(post.created_at)}</p>
                    </div>
                </div>

                {/* Backtest Data */}
                {post.post_type === 'backtest_share' && post.backtest_data && (
                    <div className="mb-5 space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                            <div className="p-3 bg-th-card rounded-xl border border-th-border-light text-center">
                                <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">초기 자본</p>
                                <p className="text-sm font-bold text-th-text">₩{Number(post.backtest_data.initial_capital).toLocaleString()}</p>
                            </div>
                            <div className="p-3 bg-th-card rounded-xl border border-th-border-light text-center">
                                <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">최종 자본</p>
                                <p className={`text-sm font-bold ${Number(post.backtest_data.final_capital) >= Number(post.backtest_data.initial_capital) ? 'text-secondary' : 'text-red-400'}`}>
                                    ₩{Number(post.backtest_data.final_capital).toLocaleString()}
                                </p>
                            </div>
                            <div className="p-3 bg-th-card rounded-xl border border-th-border-light text-center">
                                <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">총 거래</p>
                                <p className="text-sm font-bold text-th-text">{String(post.backtest_data.total_trades)}회</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-th-text-muted px-1 flex-wrap">
                            {post.backtest_data.strategy_name && (
                                <span>전략: <span className="text-th-text-secondary font-medium">{getStrategyLabel(String(post.backtest_data.strategy_name))}</span></span>
                            )}
                            {post.backtest_data.timeframe && (
                                <span>주기: <span className="text-th-text-secondary font-medium">{TIMEFRAME_LABEL_MAP[String(post.backtest_data.timeframe)] || post.backtest_data.timeframe}</span></span>
                            )}
                            {post.backtest_data.start_date && post.backtest_data.end_date && (
                                <span>기간: <span className="text-th-text-secondary font-medium">{String(post.backtest_data.start_date)} ~ {String(post.backtest_data.end_date)}</span></span>
                            )}
                            {post.backtest_data.commission_rate != null && (
                                <span>수수료: <span className="text-th-text-secondary font-medium">{(Number(post.backtest_data.commission_rate) * 100).toFixed(2)}%</span></span>
                            )}
                        </div>
                    </div>
                )}

                {/* Performance Data */}
                {post.post_type === 'performance_share' && post.performance_data && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                        <div className="p-3 bg-th-card rounded-xl border border-th-border-light">
                            <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">총 PnL</p>
                            <p className={`text-sm font-bold ${post.performance_data.total_pnl >= 0 ? 'text-secondary' : 'text-red-400'}`}>
                                ₩{Number(post.performance_data.total_pnl).toLocaleString()}
                            </p>
                        </div>
                        <div className="p-3 bg-th-card rounded-xl border border-th-border-light">
                            <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">승률</p>
                            <p className="text-sm font-bold text-th-text">{post.performance_data.win_rate}%</p>
                        </div>
                        <div className="p-3 bg-th-card rounded-xl border border-th-border-light">
                            <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">거래 수</p>
                            <p className="text-sm font-bold text-th-text">{post.performance_data.trade_count}회</p>
                        </div>
                        <div className="p-3 bg-th-card rounded-xl border border-th-border-light">
                            <p className="text-[10px] sm:text-xs text-th-text-muted mb-1">유형</p>
                            <p className={`text-sm font-bold ${post.performance_data.is_paper ? 'text-primary' : 'text-secondary'}`}>
                                {post.performance_data.is_paper ? '모의투자' : '실투자'}
                            </p>
                        </div>
                    </div>
                )}

                {post.content && (
                    <div className="text-sm text-th-text-secondary leading-relaxed whitespace-pre-wrap mb-5">
                        {post.content}
                    </div>
                )}

                <div className="flex items-center gap-4 pt-4 border-t border-th-border-light">
                    <button
                        onClick={handleLike}
                        title={isAuthenticated ? undefined : '로그인이 필요합니다'}
                        className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
                            !isAuthenticated ? 'text-th-text-muted cursor-default' :
                            post.is_liked ? 'text-red-400' : 'text-th-text-muted hover:text-red-400'
                        }`}
                    >
                        <Heart className={`w-4 h-4 ${post.is_liked ? 'fill-red-400' : ''}`} />
                        좋아요 {post.like_count}
                    </button>
                    <span className="flex items-center gap-1.5 text-sm text-th-text-muted">
                        <MessageCircle className="w-4 h-4" />
                        댓글 {post.comment_count}
                    </span>
                    {isAuthor && (
                        <button
                            onClick={handleDeletePost}
                            className="ml-auto flex items-center gap-1.5 text-xs text-th-text-muted hover:text-red-400 transition-colors"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                            삭제
                        </button>
                    )}
                </div>
            </article>

            {/* Comments */}
            <div className="glass-panel rounded-2xl p-6">
                <h3 className="text-base font-bold text-th-text mb-4 flex items-center gap-2">
                    <MessageCircle className="w-4 h-4 text-primary" />
                    댓글 {comments.length}
                </h3>

                <div className="space-y-3 mb-5">
                    {comments.length === 0 ? (
                        <p className="text-xs text-th-text-muted text-center py-6">아직 댓글이 없습니다.</p>
                    ) : (
                        comments.map((comment) => (
                            <div key={comment.id} className="flex gap-3 p-3 rounded-xl bg-th-card border border-th-border-light">
                                <div className="w-7 h-7 rounded-lg bg-th-hover flex items-center justify-center shrink-0">
                                    <UserIcon className="w-3.5 h-3.5 text-th-text-muted" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-semibold text-th-text">{comment.author_nickname ?? '익명'}</span>
                                        <span className="text-[10px] sm:text-xs text-th-text-muted">{formatDateTime(comment.created_at)}</span>
                                    </div>
                                    <p className="text-sm text-th-text-secondary leading-relaxed">{comment.content}</p>
                                </div>
                                {user?.id === comment.user_id && (
                                    <button
                                        onClick={() => handleDeleteComment(comment.id)}
                                        className="text-th-text-muted hover:text-red-400 transition-colors shrink-0"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                )}
                            </div>
                        ))
                    )}
                </div>

                {/* Add Comment or Login Prompt */}
                {isAuthenticated ? (
                    <form onSubmit={handleAddComment} className="flex items-center gap-2">
                        <input
                            value={commentText}
                            onChange={(e) => setCommentText(e.target.value)}
                            placeholder="댓글을 입력하세요..."
                            maxLength={500}
                            className="flex-1 bg-th-card border border-th-border rounded-xl px-4 py-2.5 text-sm text-th-text placeholder-th-text-muted focus:border-primary/30 transition-colors"
                        />
                        <Button type="submit" size="sm" loading={submittingComment} disabled={!commentText.trim()}>
                            <Send className="w-3.5 h-3.5" />
                        </Button>
                    </form>
                ) : (
                    <Link
                        href="/login"
                        className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-th-card border border-th-border text-sm text-th-text-secondary hover:text-primary hover:border-primary/20 transition-colors"
                    >
                        <LogIn className="w-4 h-4" />
                        로그인하여 댓글을 남겨보세요
                    </Link>
                )}
            </div>

            <DeleteConfirmationModal
                isOpen={deletingCommentId !== null}
                title="댓글 삭제"
                message="이 댓글을 삭제하시겠습니까?"
                onConfirm={executeDeleteComment}
                onCancel={() => setDeletingCommentId(null)}
            />

            <DeleteConfirmationModal
                isOpen={showDeletePost}
                title="게시글 삭제"
                message="이 게시글을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."
                onConfirm={executeDeletePost}
                onCancel={() => setShowDeletePost(false)}
            />
        </div>
    );
}
