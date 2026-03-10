'use client';
import { useState, useEffect } from 'react';
import { ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import KakaoLoginButton from '@/components/KakaoLoginButton';

export default function LoginPage() {
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    useEffect(() => {
        if (typeof window !== 'undefined' && localStorage.getItem('access_token')) {
            router.push('/dashboard');
        }
    }, [router]);

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

                <div className="space-y-6">
                    <p className="text-gray-400 text-center mb-6">
                        카카오 계정으로 간편하게 시작하세요. <br />
                        <span className="text-xs text-amber-500/80 mt-2 block">
                            * 첫 접속 시 자동으로 가입 신청되며, <br />
                            관리자 승인 완료 후 이용 가능합니다.
                        </span>
                    </p>
                    <KakaoLoginButton />
                </div>
            </div>
        </div>
    );
}
