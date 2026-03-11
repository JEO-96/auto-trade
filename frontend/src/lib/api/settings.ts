import api from '@/lib/api';

export interface BacktestSettings {
    strategy_timeframes: Record<string, string[]>;
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
