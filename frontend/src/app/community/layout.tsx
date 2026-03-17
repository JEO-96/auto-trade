'use client';

import React from 'react';
import Link from 'next/link';
import { LogIn, LayoutDashboard } from 'lucide-react';
import Logo from '@/components/Logo';
import { useAuth } from '@/contexts/AuthContext';

export default function CommunityLayout({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuth();

    return (
        <div className="min-h-screen bg-background text-white">
            {/* Top Navigation */}
            <header className="sticky top-0 z-40 bg-surface/60 backdrop-blur-2xl border-b border-white/[0.04]">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2.5">
                        <Logo size="sm" />
                    </Link>

                    <div className="flex items-center gap-2">
                        {!isLoading && (
                            isAuthenticated ? (
                                <Link
                                    href="/dashboard"
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-white/[0.03] transition-colors"
                                >
                                    <LayoutDashboard className="w-3.5 h-3.5" />
                                    대시보드
                                </Link>
                            ) : (
                                <Link
                                    href="/login"
                                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors"
                                >
                                    <LogIn className="w-3.5 h-3.5" />
                                    로그인
                                </Link>
                            )
                        )}
                    </div>
                </div>
            </header>

            {/* Content */}
            <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
                {children}
            </main>
        </div>
    );
}
