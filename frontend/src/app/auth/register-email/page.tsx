'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { completeRegistration } from '@/lib/api/auth';
import { getErrorMessage } from '@/lib/utils';

export default function RegisterEmailPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [email, setEmail] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const kakaoId = searchParams.get('kakao_id') || '';
    const kakaoToken = searchParams.get('kakao_token') || '';
    const nickname = searchParams.get('nickname') || '';

    useEffect(() => {
        if (!kakaoId || !kakaoToken) {
            router.push('/login');
        }
    }, [kakaoId, kakaoToken, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const data = await completeRegistration({
                kakao_id: kakaoId,
                kakao_token: kakaoToken,
                email,
                nickname: nickname || undefined,
            });

            localStorage.setItem('access_token', data.access_token);
            router.push('/dashboard');
        } catch (err: unknown) {
            setError(getErrorMessage(err, '이메일 등록에 실패했습니다.'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#0B0F19]">
            <div className="w-full max-w-md p-8 rounded-2xl border border-th-border bg-th-card">
                <div className="mb-8 text-center">
                    <h1 className="text-2xl font-bold text-th-text mb-2">이메일 등록</h1>
                    <p className="text-sm text-th-text-secondary">
                        카카오 계정에 이메일 정보가 없습니다.<br />
                        서비스 이용을 위해 이메일을 입력해 주세요.
                    </p>
                    {nickname && (
                        <p className="mt-3 text-sm text-th-text-secondary">
                            안녕하세요, <span className="text-th-text font-medium">{nickname}</span>님
                        </p>
                    )}
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="email-input" className="block text-sm text-th-text-secondary mb-1">이메일 주소</label>
                        <input
                            id="email-input"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="example@email.com"
                            required
                            className="w-full px-4 py-3 rounded-lg bg-th-card border border-th-border text-th-text placeholder-th-text-muted focus:outline-none focus:border-primary"
                        />
                    </div>

                    {error && (
                        <p className="text-sm text-red-400">{error}</p>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-3 rounded-lg bg-primary text-white font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading ? '등록 중...' : '가입 완료'}
                    </button>
                </form>

                <button
                    onClick={() => router.push('/login')}
                    className="mt-4 w-full text-center text-sm text-th-text-muted hover:text-th-text-secondary transition-colors"
                >
                    로그인으로 돌아가기
                </button>
            </div>
        </div>
    );
}
