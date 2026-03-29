'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { loginWithKakao } from '@/lib/api/auth';
import { useAuth } from '@/contexts/AuthContext';
import { getErrorMessage } from '@/lib/utils';

export default function KakaoCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { refreshUser } = useAuth();
    const [error, setError] = useState<string | null>(null);
    const isProcessing = useRef(false);

    useEffect(() => {
        const code = searchParams.get('code');

        if (!code) {
            setError('로그인 코드를 찾을 수 없습니다.');
            return;
        }

        // Strict Mode 이중 실행 방지 (카카오 인증 코드는 일회용)
        if (isProcessing.current) return;
        isProcessing.current = true;

        (async () => {
            try {
                const redirectUri = window.location.origin + '/auth/kakao';
                const data = await loginWithKakao(code, redirectUri);

                // 이메일 미제공 -> 이메일 입력 페이지로 이동
                if (data.requires_email) {
                    const params = new URLSearchParams({
                        kakao_id: data.kakao_id || '',
                        kakao_token: data.kakao_token || '',
                        nickname: data.nickname || '',
                    });
                    router.push(`/auth/register-email?${params.toString()}`);
                    return;
                }

                // 토큰 저장
                if (data.access_token) {
                    localStorage.setItem('access_token', data.access_token);
                }

                // AuthContext에 유저 정보 반영 후 이동 (번쩍임 방지)
                await refreshUser();
                router.push('/dashboard');
            } catch (err: unknown) {
                isProcessing.current = false;
                setError(getErrorMessage(err, '카카오 로그인에 실패했습니다.'));
            }
        })();
    }, [searchParams, refreshUser, router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="text-center">
                {error ? (
                    <div className="space-y-4">
                        <p className="text-red-500 text-lg">{error}</p>
                        <button
                            onClick={() => router.push('/login')}
                            className="text-primary hover:underline"
                        >
                            로그인 페이지로 돌아가기
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                        <p className="text-th-text text-xl">카카오 로그인 처리 중...</p>
                    </div>
                )}
            </div>
        </div>
    );
}
