export interface User {
    id: number;
    email: string;
    nickname?: string;
    is_active: boolean;
    is_admin?: boolean;
    created_at?: string;
    telegram_chat_id?: string;
    notification_trade?: boolean;
    notification_bot_status?: boolean;
    notification_system?: boolean;
    notification_interval?: string;
}

export interface NotificationSettings {
    notification_trade: boolean;
    notification_bot_status: boolean;
    notification_system: boolean;
    notification_interval: string;  // realtime, 4h, 12h, daily
}
