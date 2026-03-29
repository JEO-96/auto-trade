'use client';
import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, isAuthenticated, isLoading, logout } = useAuth();

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isLoading, isAuthenticated, pathname, router]);

    if (isLoading || !isAuthenticated) {
        return (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background">
                <LoadingSpinner message="인증 확인 중..." />
            </div>
        );
    }

    if (user && !user.is_active) {
        return (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background">
                <div className="max-w-md w-full mx-4 p-8 bg-white/[0.03] border border-white/[0.06] rounded-2xl text-center">
                    <div className="w-16 h-16 mx-auto mb-6 bg-yellow-500/10 rounded-full flex items-center justify-center">
                        <span className="text-3xl">⏳</span>
                    </div>
                    <h2 className="text-xl font-bold text-th-text mb-3">승인 대기 중</h2>
                    <p className="text-th-text-secondary text-sm leading-relaxed mb-6">
                        관리자 승인 후 서비스를 이용할 수 있습니다.<br />
                        승인이 완료되면 바로 접속 가능합니다.
                    </p>
                    <button
                        onClick={logout}
                        className="px-6 py-2.5 bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] rounded-xl text-sm text-th-text-secondary transition-colors"
                    >
                        로그아웃
                    </button>
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
