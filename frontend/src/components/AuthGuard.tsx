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

            // Verify session with backend
            // If token is invalid or expired, this will throw 401 via interceptor
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

    // Show loading state while verifying
    if (verifying) {
        return (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background backdrop-blur-md">
                <div className="flex flex-col items-center gap-6">
                    <div className="relative">
                        <div className="w-16 h-16 border-4 border-primary/10 border-t-primary rounded-full animate-spin" />
                        <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <p className="text-white font-bold text-lg tracking-widest animate-pulse uppercase">Encrypted Connection</p>
                        <p className="text-gray-500 text-xs font-medium uppercase tracking-[0.3em]">Verifying Security Access</p>
                    </div>
                </div>
            </div>
        );
    }

    // Only render children if truly authorized
    return authorized ? <>{children}</> : null;
}
