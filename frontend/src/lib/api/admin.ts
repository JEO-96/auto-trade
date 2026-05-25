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

export interface AdminDashboardSystem {
    active_bot_count: number;
    db_connection_ok: boolean;
    uptime_info: string;
}

export interface AdminDashboard {
    users: AdminDashboardUsers;
    bots: AdminDashboardBots;
    trades: AdminDashboardTrades;
    system: AdminDashboardSystem;
}

export interface PaperLabBucket {
    cash: number;
    position: {
        symbol: string;
        qty: number;
        entry_price: number;
    } | null;
    trades: Array<{
        symbol: string;
        qty: number;
        entry_price: number;
        exit_price: number;
    }>;
}

export interface PaperLabState {
    run_id: string;
    symbols: string[];
    window_start: string;
    window_end: string;
    engine: {
        buckets: Record<string, PaperLabBucket>;
    };
    last_prices: Record<string, number>;
    last_summary: {
        total_equity: number;
        realized_pnl: number;
        unrealized_pnl: number;
        open_position_count: number;
    };
    updated_at: string;
}

export interface PaperLabSnapshot {
    window_start: string;
    window_end: string;
    summary: {
        total_equity: number;
        realized_pnl: number;
        unrealized_pnl: number;
        open_position_count: number;
    };
    prices: Record<string, number>;
    created_at: string;
}

export interface PaperLabStatus {
    enabled: boolean;
    run_id: string;
    state: PaperLabState | null;
    snapshots: PaperLabSnapshot[];
}

export async function getAdminDashboard(): Promise<AdminDashboard> {
    const res = await api.get<AdminDashboard>('/admin/dashboard');
    return res.data;
}

export async function getPaperLabStatus(): Promise<PaperLabStatus> {
    const res = await api.get<PaperLabStatus>('/admin/paper-lab/status');
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
