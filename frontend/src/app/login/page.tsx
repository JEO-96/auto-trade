'use client';
import { useState } from 'react';
import { ArrowRight, Lock, Mail } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const response = await api.post('/auth/token', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            // 토큰 저장 (보안을 위해서는 HttpOnly 쿠키 권장, 여기선 구현 편의를 위해 LocalStorage 사용)
            localStorage.setItem('access_token', response.data.access_token);

            // 대시보드로 이동
            router.push('/dashboard');
        } catch (err: any) {
            setError(err.response?.data?.detail || '로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-[#0B0F19]">
            <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />

            <div className="glass-panel w-full max-w-md p-8 rounded-2xl z-10 animate-fade-in-up">
                <div className="text-center mb-8">
                    <h2 className="text-3xl font-bold mb-2">환영합니다</h2>
                    <p className="text-gray-400">트레이딩 대시보드에 접속하려면 로그인하세요.</p>
                </div>

                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 text-red-500 rounded-lg text-sm text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleLogin} className="space-y-6">
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
                                className="w-full bg-surface/50 border border-gray-700 text-white rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors disabled:opacity-50"
                                placeholder="you@example.com"
                                required
                                disabled={loading}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between items-center ml-1">
                            <label className="text-sm font-medium text-gray-300">비밀번호</label>
                            <a href="#" className="text-xs text-primary hover:text-blue-400">비밀번호를 잊으셨나요?</a>
                        </div>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Lock className="h-5 w-5 text-gray-500" />
                            </div>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-surface/50 border border-gray-700 text-white rounded-lg pl-10 pr-4 py-3 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors disabled:opacity-50"
                                placeholder="••••••••"
                                required
                                disabled={loading}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-primary hover:bg-blue-600 disabled:bg-primary/50 text-white font-semibold py-3 px-4 rounded-lg shadow-[0_0_15px_rgba(59,130,246,0.5)] transition-all flex items-center justify-center gap-2 group"
                    >
                        {loading ? '로그인 중...' : '로그인'}
                        {!loading && <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />}
                    </button>
                </form>

                <p className="mt-8 text-center text-sm text-gray-400">
                    계정이 없으신가요?{' '}
                    <Link href="/register" className="text-primary hover:text-blue-400 font-medium">
                        회원가입
                    </Link>
                </p>
            </div>
        </div>
    );
}
