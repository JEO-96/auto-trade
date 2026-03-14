'use client';
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Key, LogOut, Settings, LayoutDashboard, BarChart2, Menu, X, Shield, MessageSquare, UserCircle, Radio, Coins, TrendingUp, Trophy } from 'lucide-react';
import Logo from '@/components/Logo';
import NavItem from '@/components/ui/NavItem';
import AuthGuard from '@/components/AuthGuard';
import { useAuth } from '@/contexts/AuthContext';
import { getInitials } from '@/lib/utils';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const { user, logout } = useAuth();
    const pathname = usePathname();

    // Auto-close mobile menu on route change
    useEffect(() => {
        setIsMobileMenuOpen(false);
    }, [pathname]);

    const initials = getInitials(user?.nickname, user?.email);
    const displayName = user?.nickname || user?.email || '사용자';

    return (
        <AuthGuard>
            <div className="min-h-screen bg-background text-white flex overflow-hidden relative">
                {/* Mobile Menu Toggle - 닫힌 상태에서만 표시 */}
                <button
                    onClick={() => setIsMobileMenuOpen(true)}
                    className={`lg:hidden fixed top-4 right-4 z-50 p-2.5 bg-surface/80 backdrop-blur-xl border border-white/[0.06] rounded-xl text-gray-400 hover:text-white hover:bg-surface hover:border-white/[0.1] active:scale-95 transition-all duration-200 ${isMobileMenuOpen ? 'opacity-0 pointer-events-none scale-90' : 'opacity-100 scale-100'}`}
                    aria-label="메뉴 열기"
                >
                    <Menu className="w-5 h-5" />
                </button>

                {/* Sidebar */}
                <aside className={`
                    fixed inset-y-0 left-0 z-40 w-64 bg-surface/60 backdrop-blur-2xl border-r border-white/[0.04] flex flex-col transition-transform duration-300 ease-out
                    lg:relative lg:translate-x-0
                    ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
                `}>
                    {/* Brand + Close */}
                    <div className="p-6 pb-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2.5">
                                <Logo size="md" />
                            </div>
                            {/* 사이드바 내부 닫기 버튼 */}
                            <button
                                onClick={() => setIsMobileMenuOpen(false)}
                                className="lg:hidden p-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/[0.06] active:scale-95 transition-all duration-200"
                                aria-label="메뉴 닫기"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav aria-label="대시보드 메뉴" className="flex-1 px-3 py-4 space-y-0.5">
                        <NavItem href="/dashboard" icon={<LayoutDashboard className="w-[18px] h-[18px]" />} label="대시보드" />
                        <NavItem href="/dashboard/keys" icon={<Key className="w-[18px] h-[18px]" />} label="API 설정" />
                        <NavItem href="/dashboard/backtest" icon={<BarChart2 className="w-[18px] h-[18px]" />} label="백테스팅" />
                        <NavItem href="/dashboard/performance" icon={<TrendingUp className="w-[18px] h-[18px]" />} label="성과 분석" />
                        <NavItem href="/dashboard/live-bots" icon={<Radio className="w-[18px] h-[18px]" />} label="실시간 봇 현황" />
                        <NavItem href="/dashboard/credits" icon={<Coins className="w-[18px] h-[18px]" />} label="크레딧" />
                        <NavItem href="/dashboard/community" icon={<MessageSquare className="w-[18px] h-[18px]" />} label="커뮤니티" />
                        <NavItem href="/dashboard/community/leaderboard" icon={<Trophy className="w-[18px] h-[18px]" />} label="리더보드" />
                        <NavItem href="/dashboard/settings" icon={<Settings className="w-[18px] h-[18px]" />} label="시스템 설정" />
                        {user?.is_admin && (
                            <NavItem href="/dashboard/admin" icon={<Shield className="w-[18px] h-[18px]" />} label="사용자 관리" />
                        )}
                    </nav>

                    {/* User */}
                    <div className="p-3 mt-auto border-t border-white/[0.04]">
                        <Link
                            href="/dashboard/profile"
                            className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/[0.04] transition-colors group"
                        >
                            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-xs font-bold border border-white/[0.06] text-white/80">
                                {initials}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold truncate text-white group-hover:text-primary transition-colors">{displayName}</p>
                                <p className="text-[10px] text-gray-500 truncate">
                                    {user?.credit_balance != null
                                        ? `${user.credit_balance.toLocaleString()} 크레딧`
                                        : user?.email || ''}
                                </p>
                            </div>
                            <UserCircle className="w-4 h-4 text-gray-600 group-hover:text-primary transition-colors shrink-0" />
                        </Link>

                        <button
                            onClick={logout}
                            aria-label="로그아웃"
                            className="flex items-center gap-2.5 w-full px-4 py-2.5 text-gray-500 hover:text-red-400 hover:bg-red-500/[0.06] rounded-lg transition-colors mt-1"
                        >
                            <LogOut className="w-4 h-4" />
                            <span className="text-xs font-semibold">로그아웃</span>
                        </button>
                    </div>
                </aside>

                {/* Mobile Overlay */}
                {isMobileMenuOpen && (
                    <div
                        role="button"
                        tabIndex={0}
                        aria-label="메뉴 닫기"
                        onClick={() => setIsMobileMenuOpen(false)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setIsMobileMenuOpen(false); }}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden"
                    />
                )}

                {/* Main Content */}
                <main className="flex-1 flex flex-col h-screen relative">
                    <div className="flex-1 overflow-y-auto relative">
                        {children}
                    </div>
                </main>
            </div>
        </AuthGuard>
    );
}
