import api from '@/lib/api';
import type {
    CommunityPost,
    PostListResponse,
    PostCreateRequest,
    PostComment,
    ChatMessage,
    UserProfile,
    StrategyRating,
} from '@/types/community';
import type { User } from '@/types/user';

// Profile
export async function updateNickname(nickname: string): Promise<User> {
    const res = await api.put<User>('/community/profile/nickname', { nickname });
    return res.data;
}

export async function getUserProfile(userId: number): Promise<UserProfile> {
    const res = await api.get<UserProfile>(`/community/profile/${userId}`);
    return res.data;
}

// Posts
export async function getPosts(params: {
    page?: number;
    page_size?: number;
    post_type?: string;
}): Promise<PostListResponse> {
    const res = await api.get<PostListResponse>('/community/posts', { params });
    return res.data;
}

export async function getPost(postId: number): Promise<CommunityPost> {
    const res = await api.get<CommunityPost>(`/community/posts/${postId}`);
    return res.data;
}

export async function createPost(data: PostCreateRequest): Promise<CommunityPost> {
    const res = await api.post<CommunityPost>('/community/posts', data);
    return res.data;
}

export async function updatePost(postId: number, data: Partial<PostCreateRequest>): Promise<CommunityPost> {
    const res = await api.put<CommunityPost>(`/community/posts/${postId}`, data);
    return res.data;
}

export async function deletePost(postId: number): Promise<void> {
    await api.delete(`/community/posts/${postId}`);
}

// Likes
export async function toggleLike(postId: number): Promise<{ liked: boolean; like_count: number }> {
    const res = await api.post<{ liked: boolean; like_count: number }>(`/community/posts/${postId}/like`);
    return res.data;
}

// Comments
export async function getComments(postId: number): Promise<PostComment[]> {
    const res = await api.get<PostComment[]>(`/community/posts/${postId}/comments`);
    return res.data;
}

export async function createComment(postId: number, content: string): Promise<PostComment> {
    const res = await api.post<PostComment>(`/community/posts/${postId}/comments`, { content });
    return res.data;
}

export async function deleteComment(commentId: number): Promise<void> {
    await api.delete(`/community/comments/${commentId}`);
}

// Chat
export async function getChatMessages(afterId?: number): Promise<ChatMessage[]> {
    const params = afterId ? { after_id: afterId } : {};
    const res = await api.get<ChatMessage[]>('/community/chat', { params });
    return res.data;
}

export async function sendChatMessage(content: string): Promise<ChatMessage> {
    const res = await api.post<ChatMessage>('/community/chat', { content });
    return res.data;
}

// Strategy Reviews
export async function getStrategyReviews(strategyName: string): Promise<CommunityPost[]> {
    const res = await api.get<CommunityPost[]>(`/community/strategies/${strategyName}/reviews`);
    return res.data;
}

export async function getStrategyRating(strategyName: string): Promise<StrategyRating> {
    const res = await api.get<StrategyRating>(`/community/strategies/${strategyName}/rating`);
    return res.data;
}
