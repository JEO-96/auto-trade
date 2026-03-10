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
