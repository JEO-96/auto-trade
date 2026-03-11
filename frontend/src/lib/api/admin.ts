import api from '@/lib/api';
import type { User } from '@/types/user';

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
