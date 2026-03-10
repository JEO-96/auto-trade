export type PostType = 'backtest_share' | 'performance_share' | 'strategy_review' | 'discussion';

export interface CommunityPost {
    id: number;
    user_id: number;
    author_nickname: string | null;
    post_type: PostType;
    title: string;
    content: string | null;
    backtest_data: Record<string, unknown> | null;
    performance_data: PerformanceData | null;
    strategy_name: string | null;
    rating: number | null;
    like_count: number;
    comment_count: number;
    is_liked: boolean;
    created_at: string;
}

export interface PerformanceData {
    symbol: string;
    strategy: string;
    period: string;
    total_pnl: number;
    win_rate: number;
    trade_count: number;
    is_paper: boolean;
}

export interface PostListResponse {
    posts: CommunityPost[];
    total: number;
    page: number;
    page_size: number;
}

export interface PostCreateRequest {
    post_type: PostType;
    title: string;
    content?: string;
    backtest_data?: Record<string, unknown>;
    performance_data?: PerformanceData;
    strategy_name?: string;
    rating?: number;
}

export interface PostComment {
    id: number;
    user_id: number;
    author_nickname: string | null;
    content: string;
    created_at: string;
}

export interface ChatMessage {
    id: number;
    user_id: number;
    author_nickname: string | null;
    content: string;
    created_at: string;
}

export interface UserProfile {
    id: number;
    nickname: string | null;
    email: string;
    created_at: string | null;
    post_count: number;
}

export interface StrategyRating {
    strategy_name: string;
    average_rating: number;
    review_count: number;
}
