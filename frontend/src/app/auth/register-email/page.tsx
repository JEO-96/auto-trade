'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api from '@/lib/api';

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
            const response = await api.post('/auth/kakao/complete', {
                kakao_id: kakaoId,
                kakao_token: kakaoToken,
                email,
                nickname,
            });

            localStorage.setItem('access_token', response.data.access_token);
            router.push('/dashboard');
        } catch (err: any) {
            setError(err.response?.data?.detail || '이메일 등록에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#0B0F19]">
            <div className="w-full max-w-md p-8 rounded-2xl border border-white/10 bg-white/[0.03]">
                <div className="mb-8 text-center">
                    <h1 className="text-2xl font-bold text-white mb-2">이메일 등록</h1>
                    <p className="text-sm text-gray-400">
                        카카오 계정에 이메일 정보가 없습니다.<br />
                        서비스 이용을 위해 이메일을 입력해 주세요.
                    </p>
                    {nickname && (
                        <p className="mt-3 text-sm text-gray-300">
                            안녕하세요, <span className="text-white font-medium">{nickname}</span>님
                        </p>
                    )}
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">이메일 주소</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="example@email.com"
                            required
                            className="w-full px-4 py-3 rounded-lg bg-white/[0.05] border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-primary"
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
                    className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-300 transition-colors"
                >
                    로그인으로 돌아가기
                </button>
            </div>
        </div>
    );
}
