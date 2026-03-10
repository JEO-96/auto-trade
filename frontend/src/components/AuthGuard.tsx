'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import api from '@/lib/api';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [authorized, setAuthorized] = useState(false);
    const [verifying, setVerifying] = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const token = localStorage.getItem('access_token');

            if (!token) {
                setAuthorized(false);
                router.push('/login');
                return;
            }

            await api.get('/auth/me');
            setAuthorized(true);
        } catch (error) {
            console.error("Auth verification failed:", error);
            setAuthorized(false);
            localStorage.removeItem('access_token');
            router.push('/login');
        } finally {
            setVerifying(false);
        }
    }, [router]);

    useEffect(() => {
        checkAuth();
    }, [pathname, checkAuth]);

    if (verifying) {
        return (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
                    <p className="text-sm text-gray-500 font-medium">인증 확인 중...</p>
                </div>
            </div>
        );
    }

    return authorized ? <>{children}</> : null;
}
