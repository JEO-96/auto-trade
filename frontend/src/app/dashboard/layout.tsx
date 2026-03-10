'use client';
import React, { useState } from 'react';
import { Activity, Key, LogOut, Settings, User, LayoutDashboard, Database, BarChart2, Menu, X } from 'lucide-react';
import NavItem from '@/components/ui/NavItem';
import AuthGuard from '@/components/AuthGuard';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    return (
        <AuthGuard>
            <div className="min-h-screen bg-background text-white flex overflow-hidden relative">
                {/* Mobile Menu Toggle */}
                <button
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="lg:hidden fixed top-6 right-6 z-50 p-3 bg-primary/20 backdrop-blur-xl border border-primary/30 rounded-xl text-primary shadow-glow-primary hover:bg-primary/30 transition-all"
                    aria-label="Toggle Menu"
                >
                    {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>

                {/* Sidebar Navigation */}
                <aside className={`
                    fixed inset-y-0 left-0 z-40 w-72 bg-surface/80 backdrop-blur-3xl border-r border-white/5 flex flex-col transition-transform duration-500 ease-in-out
                    lg:relative lg:translate-x-0
                    ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
                `}>
                    {/* Brand Logo */}
                    <div className="p-8 mb-4">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center border border-primary/30 shadow-glow-primary">
                                <Activity className="w-6 h-6 text-primary" />
                            </div>
                            <div>
                                <span className="text-xl font-extrabold tracking-tight text-white block leading-none">
                                    MOMENTUM
                                </span>
                                <span className="text-[10px] font-bold text-primary tracking-[0.2em] uppercase">
                                    Trading Bot
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Navigation Links */}
                    <nav className="flex-1 px-4 space-y-1">
                        <NavItem href="/dashboard" icon={<LayoutDashboard className="w-5 h-5" />} label="대시보드" />
                        <NavItem href="/dashboard/keys" icon={<Key className="w-5 h-5" />} label="API 설정" />
                        <NavItem href="/dashboard/backtest" icon={<BarChart2 className="w-5 h-5" />} label="백테스팅" />
                        <NavItem href="/dashboard/settings" icon={<Settings className="w-5 h-5" />} label="시스템 설정" />
                    </nav>

                    {/* User Section */}
                    <div className="p-4 mt-auto border-t border-white/5 bg-black/20">
                        <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 mb-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-sm font-bold border border-white/10 uppercase">
                                JD
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold truncate text-white">James Doe</p>
                                <p className="text-[10px] text-gray-500 truncate">Premium Account</p>
                            </div>
                        </div>

                        <button
                            onClick={() => {
                                localStorage.removeItem('access_token');
                                window.location.href = '/';
                            }}
                            className="flex items-center gap-3 w-full px-4 py-3 text-gray-400 hover:text-danger hover:bg-danger/10 rounded-xl transition-all duration-300 group"
                        >
                            <LogOut className="w-5 h-5 group-hover:scale-110 transition-transform" />
                            <span className="text-sm font-bold">로그아웃</span>
                        </button>
                    </div>

                    {/* Decorative background for sidebar */}
                    <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-primary/5 to-transparent pointer-events-none" />
                </aside>

                {/* Mobile Overlay */}
                {isMobileMenuOpen && (
                    <div
                        onClick={() => setIsMobileMenuOpen(false)}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden animate-in fade-in duration-300"
                    />
                )}

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-screen relative bg-dot-pattern">
                    {/* Top header decoration */}
                    <div className="h-1 bg-gradient-to-r from-primary via-accent to-secondary opacity-50 w-full shrink-0" />

                    {/* Ambient background glows for main area */}
                    <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
                    <div className="absolute bottom-[-10%] left-[-5%] w-[30%] h-[30%] bg-accent/5 rounded-full blur-[100px] pointer-events-none" />

                    <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                        {children}
                    </div>
                </main>
            </div>
        </AuthGuard>
    );
}
