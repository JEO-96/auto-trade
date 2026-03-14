import api from '@/lib/api';
import type { User } from '@/types/user';

// -------- Admin Dashboard Types --------
export interface AdminDashboardUsers {
    total: number;
    active: number;
    pending: number;
    new_today: number;
}

export interface AdminDashboardBots {
    total_configs: number;
    running_now: number;
    live_bots: number;
    paper_bots: number;
}

export interface AdminDashboardTrades {
    total_trades: number;
    today_trades: number;
    total_pnl: number;
    today_pnl: number;
}

export interface AdminDashboardRevenue {
    total_credit_purchased: number;
    total_profit_fees: number;
    total_loss_refunds: number;
    net_revenue: number;
}

export interface AdminDashboardSystem {
    active_bot_count: number;
    db_connection_ok: boolean;
    uptime_info: string;
}

export interface AdminDashboard {
    users: AdminDashboardUsers;
    bots: AdminDashboardBots;
    trades: AdminDashboardTrades;
    revenue: AdminDashboardRevenue;
    system: AdminDashboardSystem;
}

export async function getAdminDashboard(): Promise<AdminDashboard> {
    const res = await api.get<AdminDashboard>('/admin/dashboard');
    return res.data;
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
