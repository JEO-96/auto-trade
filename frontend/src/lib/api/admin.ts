import api from '@/lib/api';
import type { User } from '@/types/user';

export interface AllowedTimeframe {
    id: number;
    timeframe: string;
    label: string;
    display_order: number;
    is_active: boolean;
}

export interface TimeframeOption {
    timeframe: string;
    label: string;
}

export async function getUsers(): Promise<User[]> {
    const res = await api.get<User[]>('/admin/users');
    return res.data;
}

export async function getPendingUsers(): Promise<User[]> {
    const res = await api.get<User[]>('/admin/users/pending');
    return res.data;
}

export async function approveUser(userId: number): Promise<void> {
    await api.post(`/admin/users/${userId}/approve`);
}

export async function rejectUser(userId: number): Promise<void> {
    await api.post(`/admin/users/${userId}/reject`);
}

// -------- 캔들 주기 관리 --------

export async function getAllTimeframeOptions(): Promise<TimeframeOption[]> {
    const res = await api.get<TimeframeOption[]>('/admin/timeframes/all-options');
    return res.data;
}

export async function getAllowedTimeframes(): Promise<AllowedTimeframe[]> {
    const res = await api.get<AllowedTimeframe[]>('/admin/timeframes');
    return res.data;
}

export async function addAllowedTimeframe(data: {
    timeframe: string;
    label: string;
    display_order?: number;
    is_active?: boolean;
}): Promise<AllowedTimeframe> {
    const res = await api.post<AllowedTimeframe>('/admin/timeframes', data);
    return res.data;
}

export async function updateAllowedTimeframe(
    id: number,
    data: { label?: string; display_order?: number; is_active?: boolean },
): Promise<AllowedTimeframe> {
    const res = await api.put<AllowedTimeframe>(`/admin/timeframes/${id}`, data);
    return res.data;
}

export async function deleteAllowedTimeframe(id: number): Promise<void> {
    await api.delete(`/admin/timeframes/${id}`);
}
