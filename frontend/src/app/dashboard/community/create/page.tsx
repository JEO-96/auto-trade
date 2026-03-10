'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Star } from 'lucide-react';
import Link from 'next/link';
import PageContainer from '@/components/ui/PageContainer';
import Button from '@/components/ui/Button';
import Input, { SelectInput } from '@/components/ui/Input';
import { createPost } from '@/lib/api/community';
import type { PostType, PostCreateRequest } from '@/types/community';

const STRATEGIES = [
    'momentum_breakout_basic',
    'momentum_breakout_pro_stable',
    'momentum_breakout_pro_aggressive',
    'momentum_breakout_elite',
];

export default function CreatePostPage() {
    const router = useRouter();
    const [postType, setPostType] = useState<PostType>('discussion');
    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [strategyName, setStrategyName] = useState(STRATEGIES[0]);
    const [rating, setRating] = useState(5);
    const [hoverRating, setHoverRating] = useState(0);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    // Performance share fields
    const [perfSymbol, setPerfSymbol] = useState('BTC/KRW');
    const [perfPnl, setPerfPnl] = useState('');
    const [perfWinRate, setPerfWinRate] = useState('');
    const [perfTradeCount, setPerfTradeCount] = useState('');
    const [perfPeriod, setPerfPeriod] = useState('');
    const [perfIsPaper, setPerfIsPaper] = useState(true);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!title.trim()) {
            setError('제목을 입력해주세요.');
            return;
        }

        if (postType === 'strategy_review' && !strategyName) {
            setError('전략을 선택해주세요.');
            return;
        }

        setSubmitting(true);
        try {
            const data: PostCreateRequest = {
                post_type: postType,
                title: title.trim(),
                content: content.trim() || undefined,
            };

            if (postType === 'strategy_review') {
                data.strategy_name = strategyName;
                data.rating = rating;
            }

            if (postType === 'performance_share') {
                data.performance_data = {
                    symbol: perfSymbol,
                    strategy: strategyName,
                    period: perfPeriod || '미지정',
                    total_pnl: Number(perfPnl) || 0,
                    win_rate: Number(perfWinRate) || 0,
                    trade_count: Number(perfTradeCount) || 0,
                    is_paper: perfIsPaper,
                };
            }

            await createPost(data);
            router.push('/dashboard/community');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '게시글 작성에 실패했습니다.';
            setError(msg);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <PageContainer maxWidth="max-w-3xl">
            <Link
                href="/dashboard/community"
                className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-white transition-colors mb-6"
            >
                <ArrowLeft className="w-3.5 h-3.5" />
                커뮤니티로 돌아가기
            </Link>

            <div className="glass-panel rounded-2xl p-6">
                <h1 className="text-xl font-bold text-white mb-6">새 글 작성</h1>

                <form onSubmit={handleSubmit} className="space-y-5">
                    {/* Post Type */}
                    <SelectInput
                        type="select"
                        label="글 유형"
                        value={postType}
                        onChange={(e) => setPostType(e.target.value as PostType)}
                    >
                        <option value="discussion">자유 토론</option>
                        <option value="backtest_share">백테스트 공유</option>
                        <option value="performance_share">수익률 공유</option>
                        <option value="strategy_review">전략 리뷰</option>
                    </SelectInput>

                    {/* Title */}
                    <Input
                        label="제목"
                        placeholder="제목을 입력하세요"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        maxLength={100}
                    />

                    {/* Content */}
                    <div>
                        <label className="text-xs text-gray-500 font-medium mb-1.5 block">내용</label>
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="내용을 입력하세요..."
                            rows={6}
                            className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-primary/30 transition-colors resize-none"
                        />
                    </div>

                    {/* Strategy Review Fields */}
                    {postType === 'strategy_review' && (
                        <div className="space-y-4 p-4 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                            <SelectInput
                                type="select"
                                label="전략"
                                value={strategyName}
                                onChange={(e) => setStrategyName(e.target.value)}
                            >
                                {STRATEGIES.map((s) => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </SelectInput>

                            <div>
                                <label className="text-xs text-gray-500 font-medium mb-2 block">평점</label>
                                <div className="flex items-center gap-1">
                                    {[1, 2, 3, 4, 5].map((i) => (
                                        <button
                                            key={i}
                                            type="button"
                                            onClick={() => setRating(i)}
                                            onMouseEnter={() => setHoverRating(i)}
                                            onMouseLeave={() => setHoverRating(0)}
                                            className="p-0.5 transition-transform hover:scale-110"
                                        >
                                            <Star
                                                className={`w-6 h-6 ${
                                                    i <= (hoverRating || rating)
                                                        ? 'text-amber-400 fill-amber-400'
                                                        : 'text-gray-600'
                                                }`}
                                            />
                                        </button>
                                    ))}
                                    <span className="text-sm text-gray-400 ml-2 font-medium">{rating}/5</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Performance Share Fields */}
                    {postType === 'performance_share' && (
                        <div className="space-y-4 p-4 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                            <div className="grid grid-cols-2 gap-3">
                                <Input
                                    label="심볼"
                                    value={perfSymbol}
                                    onChange={(e) => setPerfSymbol(e.target.value)}
                                    placeholder="BTC/KRW"
                                />
                                <Input
                                    label="기간"
                                    value={perfPeriod}
                                    onChange={(e) => setPerfPeriod(e.target.value)}
                                    placeholder="예: 2024.01~03"
                                />
                            </div>
                            <div className="grid grid-cols-3 gap-3">
                                <Input
                                    label="총 손익 (원)"
                                    type="number"
                                    value={perfPnl}
                                    onChange={(e) => setPerfPnl(e.target.value)}
                                    placeholder="0"
                                />
                                <Input
                                    label="승률 (%)"
                                    type="number"
                                    value={perfWinRate}
                                    onChange={(e) => setPerfWinRate(e.target.value)}
                                    placeholder="0"
                                />
                                <Input
                                    label="거래 수"
                                    type="number"
                                    value={perfTradeCount}
                                    onChange={(e) => setPerfTradeCount(e.target.value)}
                                    placeholder="0"
                                />
                            </div>
                            <SelectInput
                                type="select"
                                label="전략"
                                value={strategyName}
                                onChange={(e) => setStrategyName(e.target.value)}
                            >
                                {STRATEGIES.map((s) => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </SelectInput>
                            <div className="flex items-center gap-3">
                                <label className="text-xs text-gray-500 font-medium">투자 유형:</label>
                                <button
                                    type="button"
                                    onClick={() => setPerfIsPaper(true)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                                        perfIsPaper ? 'bg-primary/10 text-primary border border-primary/20' : 'text-gray-500 border border-transparent'
                                    }`}
                                >
                                    모의투자
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setPerfIsPaper(false)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                                        !perfIsPaper ? 'bg-secondary/10 text-secondary border border-secondary/20' : 'text-gray-500 border border-transparent'
                                    }`}
                                >
                                    실투자
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Backtest Share Note */}
                    {postType === 'backtest_share' && (
                        <div className="p-4 bg-primary/[0.04] rounded-xl border border-primary/10">
                            <p className="text-xs text-primary/80 leading-relaxed">
                                백테스트 결과는 백테스팅 페이지에서 완료 후 &quot;커뮤니티 공유&quot; 버튼으로 자동 첨부할 수 있습니다.
                                직접 결과를 설명하려면 내용에 작성해주세요.
                            </p>
                        </div>
                    )}

                    {error && (
                        <p className="text-xs text-red-400 font-medium">{error}</p>
                    )}

                    <div className="flex items-center gap-3 pt-2">
                        <Button type="submit" loading={submitting}>
                            게시하기
                        </Button>
                        <Link href="/dashboard/community">
                            <Button variant="ghost" type="button">취소</Button>
                        </Link>
                    </div>
                </form>
            </div>
        </PageContainer>
    );
}
