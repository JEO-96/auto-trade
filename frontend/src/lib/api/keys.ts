import api from '@/lib/api';
import type { ExchangeKeyPreview, ExchangeKeyCreateRequest } from '@/types/keys';

export async function getKeys(): Promise<ExchangeKeyPreview[]> {
    const res = await api.get<ExchangeKeyPreview[]>('/keys/');
    return res.data;
}

export async function saveKey(data: ExchangeKeyCreateRequest): Promise<void> {
    await api.post('/keys/', data);
}

export async function deleteKey(keyId: number): Promise<void> {
    await api.delete(`/keys/${keyId}`);
}

export interface BalanceItem {
    currency: string;
    total: number;
    free: number;
    used: number;
    avg_buy_price: number | null;
}

export async function getUpbitBalance(): Promise<BalanceItem[]> {
    const res = await api.get<{ balances: BalanceItem[] }>('/keys/balance');
    return res.data.balances;
}
