import api from '@/lib/api';
import type { BotConfig, TradeLog, BotStatus } from '@/types/bot';

export async function getBotList(): Promise<BotConfig[]> {
    const res = await api.get<BotConfig[]>('/bot/list');
    return res.data;
}

export async function getBotStatus(botId: number): Promise<BotStatus> {
    const res = await api.get<BotStatus>(`/bot/status/${botId}`);
    return res.data;
}

export async function startBot(botId: number): Promise<void> {
    await api.post(`/bot/start/${botId}`);
}

export async function stopBot(botId: number): Promise<void> {
    await api.post(`/bot/stop/${botId}`);
}

export async function getBotLogs(botId: number): Promise<TradeLog[]> {
    const res = await api.get<TradeLog[]>(`/bot/logs/${botId}`);
    return res.data;
}
