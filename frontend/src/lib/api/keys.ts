import api from '@/lib/api';
import type { ExchangeKeyPreview, ExchangeKeyCreateRequest, BalanceItem } from '@/types/keys';

export type { BalanceItem } from '@/types/keys';

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

export async function getUpbitBalance(): Promise<BalanceItem[]> {
    const res = await api.get<{ balances: BalanceItem[] }>('/keys/balance');
    return res.data.balances;
}
