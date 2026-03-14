import api from '@/lib/api';
import type { User, NotificationSettings } from '@/types/user';

export async function getMe(): Promise<User> {
    const res = await api.get<User>('/auth/me');
    return res.data;
}

export interface KakaoLoginResponse {
    access_token?: string;
    requires_email?: boolean;
    kakao_id?: string;
    kakao_token?: string;
    nickname?: string;
}

export async function loginWithKakao(
    code: string,
    redirectUri: string,
): Promise<KakaoLoginResponse> {
    const res = await api.post<KakaoLoginResponse>('/auth/kakao', {
        code,
        redirect_uri: redirectUri,
    });
    return res.data;
}

export interface CompleteRegistrationData {
    kakao_id: string;
    kakao_token: string;
    email: string;
    nickname?: string;
}

export async function completeRegistration(
    data: CompleteRegistrationData,
): Promise<{ access_token: string }> {
    const res = await api.post<{ access_token: string }>('/auth/kakao/complete', data);
    return res.data;
}

// Notification Settings
export async function getNotificationSettings(): Promise<NotificationSettings> {
    const res = await api.get<NotificationSettings>('/auth/notifications');
    return res.data;
}

export async function updateNotificationSettings(
    data: NotificationSettings,
): Promise<NotificationSettings> {
    const res = await api.put<NotificationSettings>('/auth/notifications', data);
    return res.data;
}
