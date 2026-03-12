'use client';

import React from 'react';
import Link from 'next/link';
import { Activity, LogIn, LayoutDashboard } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function CommunityLayout({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuth();

    return (
        <div className="min-h-screen bg-background text-white">
            {/* Top Navigation */}
            <header className="sticky top-0 z-40 bg-surface/60 backdrop-blur-2xl border-b border-white/[0.04]">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
                            <Activity className="w-4 h-4 text-primary" />
                        </div>
                        <div>
                            <span className="text-sm font-extrabold tracking-tight text-white block leading-none">
                                BACKTESTED
                            </span>
                            <span className="text-[8px] font-semibold text-gray-500 tracking-widest uppercase">
                                커뮤니티
                            </span>
                        </div>
                    </Link>

                    <div className="flex items-center gap-2">
                        {!isLoading && (
                            isAuthenticated ? (
                                <Link
                                    href="/dashboard"
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-400 hover:text-white hover:bg-white/[0.04] transition-colors"
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
