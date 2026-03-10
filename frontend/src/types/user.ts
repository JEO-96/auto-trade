export interface User {
    id: number;
    email: string;
    nickname?: string;
    is_active: boolean;
    is_admin?: boolean;
    created_at?: string;
}
