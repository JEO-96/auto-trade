import api from '@/lib/api';
import type { UserStrategy } from '@/types/backtest';

export async function getUserStrategies(): Promise<UserStrategy[]> {
    const res = await api.get<UserStrategy[]>('/strategies/');
    return res.data;
}

export async function createStrategyFromBacktest(
    historyId: number,
    name: string,
): Promise<UserStrategy> {
    const res = await api.post<UserStrategy>(
        `/strategies/from-backtest/${historyId}?name=${encodeURIComponent(name)}`,
    );
    return res.data;
}

export async function createUserStrategy(data: {
    name: string;
    base_strategy_name: string;
    custom_params: Record<string, unknown>;
    backtest_history_id?: number;
}): Promise<UserStrategy> {
    const res = await api.post<UserStrategy>('/strategies/', data);
    return res.data;
}

export async function deleteUserStrategy(id: number): Promise<void> {
    await api.delete(`/strategies/${id}`);
}
