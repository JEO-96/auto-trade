import api from '@/lib/api';
import type { BacktestFormParams, BacktestTaskStatus, BacktestHistoryItem, BacktestHistoryDetail, RunBacktestResponse, DualMomentumRequest, PortfolioBacktestResult } from '@/types/backtest';
import type { CommunityPost } from '@/types/community';

export type { RunBacktestResponse } from '@/types/backtest';

export async function runDualMomentumBacktest(
    params: DualMomentumRequest,
): Promise<PortfolioBacktestResult> {
    const res = await api.post<PortfolioBacktestResult>('/backtest/dual_momentum/', params);
    return res.data;
}

export async function runPortfolioBacktest(
    params: BacktestFormParams,
): Promise<RunBacktestResponse> {
    const res = await api.post<RunBacktestResponse>('/backtest/portfolio', params);
    return res.data;
}

export async function getBacktestStatus(
    taskId: string,
): Promise<BacktestTaskStatus> {
    const res = await api.get<BacktestTaskStatus>(`/backtest/status/${taskId}`);
    return res.data;
}

export async function getBacktestHistory(
    page: number = 1,
    pageSize: number = 20,
): Promise<BacktestHistoryItem[]> {
    const res = await api.get<BacktestHistoryItem[]>('/backtest/history', {
        params: { page, page_size: pageSize },
    });
    return res.data;
}

export async function getBacktestHistoryDetail(
    historyId: number,
): Promise<BacktestHistoryDetail> {
    const res = await api.get<BacktestHistoryDetail>(`/backtest/history/${historyId}`);
    return res.data;
}

export async function updateBacktestHistoryTitle(
    historyId: number,
    title: string,
): Promise<void> {
    await api.patch(`/backtest/history/${historyId}`, { title });
}

export async function deleteBacktestHistory(
    historyId: number,
): Promise<void> {
    await api.delete(`/backtest/history/${historyId}`);
}

export async function shareBacktestToCommunity(
    historyId: number,
    title: string,
    content?: string,
): Promise<CommunityPost> {
    const params: Record<string, string> = { title };
    if (content) params.content = content;
    const res = await api.post<CommunityPost>(`/backtest/history/${historyId}/share`, null, { params });
    return res.data;
}
