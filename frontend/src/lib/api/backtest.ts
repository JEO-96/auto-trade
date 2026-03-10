import api from '@/lib/api';
import type { BacktestFormParams, BacktestTaskStatus } from '@/types/backtest';

export interface RunBacktestResponse {
    status: 'running' | 'success';
    task_id?: string;
    message?: string;
    [key: string]: unknown;
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
