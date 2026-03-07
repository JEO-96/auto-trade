'use client';
import { useState } from 'react';
import { ArrowRight, Lock, Mail, User } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function RegisterPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await api.post('/auth/register', {
                email: email,
                password: password
            });

            // 성공 시 로그인 페이지로 이동
            alert('회원가입이 완료되었습니다! 로그인해주세요.');
            router.push('/login');
        } catch (err: any) {
            setError(err.response?.data?.detail || '회원가입에 실패했습니다. 올바른 형식을 입력해주세요 (예: 유효한 이메일, 8자리 이상 비밀번호).');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-[#0B0F19]">
            <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] bg-secondary/20 rounded-full blur-[120px] pointer-events-none" />

            <div className="glass-panel w-full max-w-md p-8 rounded-2xl z-10 animate-fade-in-up">
                <div className="text-center mb-8">
                    <h2 className="text-3xl font-bold mb-2">계정 생성</h2>
                    <p className="text-gray-400">모멘텀 돌파 전략 자동화를 시작하세요</p>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 text-red-500 rounded-lg text-sm text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleRegister} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 ml-1">이메일 주소</label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Mail className="h-5 w-5 text-gray-500" />
                            </div>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-surface/50 border border-gray-700 text-white rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-colors disabled:opacity-50"
                                placeholder="you@example.com"
                                required
                                disabled={loading}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300 ml-1">비밀번호</label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Lock className="h-5 w-5 text-gray-500" />
                            </div>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-surface/50 border border-gray-700 text-white rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-colors disabled:opacity-50"
                                placeholder="••••••••"
                                minLength={8}
                                required
                                disabled={loading}
                            />
                            <p className="text-xs text-gray-500 mt-1 ml-1">최소 8자 이상 입력해주세요</p>
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-secondary hover:bg-emerald-600 disabled:bg-secondary/50 text-white font-semibold py-3 px-4 rounded-lg shadow-[0_0_15px_rgba(16,185,129,0.4)] transition-all flex items-center justify-center gap-2 group"
                    >
                        {loading ? '처리 중...' : '계정 생성하기'}
                        {!loading && <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />}
                    </button>
                </form>

                <p className="mt-8 text-center text-sm text-gray-400">
                    이미 계정이 있으신가요?{' '}
                    <Link href="/login" className="text-secondary hover:text-emerald-400 font-medium">
                        로그인
                    </Link>
                </p>
            </div>
        </div>
    );
}
