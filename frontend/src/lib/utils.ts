import { isAxiosError } from 'axios';

/**
 * 사용자 이니셜 생성 (닉네임 또는 이메일에서 추출)
 */
export function getInitials(nickname?: string, email?: string): string {
    if (nickname) {
        return nickname.slice(0, 2).toUpperCase();
    }
    if (email) {
        return email.slice(0, 2).toUpperCase();
    }
    return '??';
}

/**
 * 에러 객체에서 사용자 표시용 메시지를 추출
 * - Axios 에러: response.data.detail 우선
 * - 일반 Error: message 사용
 * - 기타: 기본 메시지 반환
 */
export function getErrorMessage(err: unknown, fallback = '알 수 없는 오류가 발생했습니다.'): string {
    if (isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
            return detail;
        }
    }
    if (err instanceof Error) {
        return err.message;
    }
    return fallback;
}
