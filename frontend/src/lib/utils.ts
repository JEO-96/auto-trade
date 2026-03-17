import { isAxiosError } from 'axios';
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** shadcn/ui class merge utility */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * KRW 금액 포맷 (소수점 버림)
 * formatKRW(1234567) → "₩1,234,567"
 */
export function formatKRW(amount: number): string {
    return `₩${Math.floor(amount).toLocaleString()}`;
}

/**
 * 암호화폐 수량 포맷
 * formatCryptoAmount(0.12345678, 4) → "0.1235"
 */
export function formatCryptoAmount(amount: number, decimals = 4): string {
    return amount.toFixed(decimals);
}

/**
 * 한국어 날짜 포맷 (날짜만)
 * formatDate("2025-01-15T12:00:00") → "2025년 1월 15일"
 */
export function formatDate(dateStr: string): string {
    try {
        return new Date(dateStr).toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    } catch {
        return dateStr;
    }
}

/**
 * 한국어 날짜+시간 포맷
 * formatDateTime("2025-01-15T12:30:00") → "2025년 1월 15일 오후 12:30"
 */
export function formatDateTime(dateStr: string): string {
    try {
        return new Date(dateStr).toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch {
        return dateStr;
    }
}

/**
 * 간결한 날짜 포맷 (숫자만)
 * formatDateCompact("2025-01-15T12:00:00") → "2025. 01. 15"
 */
export function formatDateCompact(dateStr: string): string {
    try {
        return new Date(dateStr).toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        });
    } catch {
        return dateStr;
    }
}

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
