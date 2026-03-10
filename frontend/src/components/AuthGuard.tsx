'use client';
import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { isAuthenticated, isLoading } = useAuth();

    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isLoading, isAuthenticated, pathname, router]);

    if (isLoading) {
        return (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background">
                <LoadingSpinner message="인증 확인 중..." />
            </div>
        );
    }

    return isAuthenticated ? <>{children}</> : null;
}
