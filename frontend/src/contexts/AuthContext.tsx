'use client';

import React, {
    createContext,
    useContext,
    useState,
    useEffect,
    useCallback,
    useMemo,
} from 'react';
import { useRouter } from 'next/navigation';
import type { User } from '@/types/user';
import { getMe } from '@/lib/api/auth';

interface AuthContextValue {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    logout: () => void;
    /** 인증 상태를 다시 확인합니다 (토큰 갱신 후 등) */
    refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchUser = useCallback(async () => {
        try {
            const token =
                typeof window !== 'undefined'
                    ? localStorage.getItem('access_token')
                    : null;

            if (!token) {
                setUser(null);
                return;
            }

            const userData = await getMe();
            setUser(userData);
        } catch {
            setUser(null);
            if (typeof window !== 'undefined') {
                localStorage.removeItem('access_token');
            }
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const logout = useCallback(() => {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('access_token');
        }
        setUser(null);
        router.push('/login');
    }, [router]);

    const refreshUser = useCallback(async () => {
        setIsLoading(true);
        await fetchUser();
    }, [fetchUser]);

    const value = useMemo<AuthContextValue>(
        () => ({
            user,
            isLoading,
            isAuthenticated: !!user,
            logout,
            refreshUser,
        }),
        [user, isLoading, logout, refreshUser],
    );

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth는 AuthProvider 내부에서 사용해야 합니다.');
    }
    return context;
}
