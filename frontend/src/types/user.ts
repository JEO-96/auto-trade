export interface User {
    id: number;
    email: string;
    nickname?: string;
    is_active: boolean;
    is_admin?: boolean;
    created_at?: string;
    credit_balance?: number;
    telegram_chat_id?: string;
    notification_trade?: boolean;
    notification_bot_status?: boolean;
    notification_system?: boolean;
}

export interface NotificationSettings {
    notification_trade: boolean;
    notification_bot_status: boolean;
    notification_system: boolean;
}

export interface CreditBalance {
    balance: number;
    total_earned: number;
    total_spent: number;
}

export interface CreditTransaction {
    id: number;
    amount: number;
    balance_after: number;
    tx_type: string;
    reference_id?: number;
    description?: string;
    created_at: string;
}

export interface CreditTransactionList {
    transactions: CreditTransaction[];
    total: number;
    page: number;
    page_size: number;
}
