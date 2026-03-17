import api from '@/lib/api';

export interface BacktestSettings {
    strategy_timeframes: Record<string, string[]>;
}

export interface StrategyItem {
    value: string;
    label: string;
    is_public?: boolean;
    status?: 'confirmed' | 'testing';
}

export interface StrategiesResponse {
    strategies: StrategyItem[];
    backtest_aliases: StrategyItem[];
}

export async function getStrategies(): Promise<StrategiesResponse> {
    const res = await api.get<StrategiesResponse>('/settings/strategies');
    return res.data;
}

export async function updateStrategyVisibility(
    visibility: Record<string, boolean>,
): Promise<{ strategies: StrategyItem[] }> {
    const res = await api.put('/settings/strategies/visibility', { visibility });
    return res.data;
}

export async function getBacktestSettings(): Promise<BacktestSettings> {
    const res = await api.get<BacktestSettings>('/settings/backtest');
    return res.data;
}

export async function updateBacktestSettings(
    data: BacktestSettings,
): Promise<void> {
    await api.put('/settings/backtest', data);
}
