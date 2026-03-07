import React from 'react';
import { Activity, Key, LogOut, Settings, User } from 'lucide-react';
import NavItem from '@/components/ui/NavItem';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <div className="min-h-screen bg-[#0B0F19] text-white flex">
            {/* Sidebar Navigation */}
            <aside className="w-64 border-r border-gray-800 bg-surface/30 backdrop-blur-xl flex flex-col p-4 z-20">
                <div className="flex items-center gap-3 mb-10 px-2 mt-4">
                    <Activity className="w-8 h-8 text-primary" />
                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
                        모멘텀 매매봇
                    </span>
                </div>

                <nav className="flex-1 space-y-2">
                    <NavItem href="/dashboard" icon={<Activity className="w-5 h-5" />} label="대시보드" />
                    <NavItem href="/dashboard/keys" icon={<Key className="w-5 h-5" />} label="거래소 API 설정" />
                    <NavItem href="/dashboard/backtest" icon={<Settings className="w-5 h-5" />} label="전략 백테스팅" />
                    <NavItem href="#" icon={<User className="w-5 h-5" />} label="내 정보" />
                </nav>

                <div className="mt-auto border-t border-gray-800 pt-4">
                    <a href="/" className="flex items-center gap-3 w-full px-4 py-3 text-gray-400 hover:text-danger hover:bg-danger/10 rounded-lg transition-colors cursor-pointer">
                        <LogOut className="w-5 h-5" />
                        <span className="font-medium">로그아웃</span>
                    </a>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto relative">
                <div className="absolute top-0 right-0 w-[40%] h-[40%] bg-accent/10 rounded-full blur-[120px] pointer-events-none" />
                {children}
            </main>
        </div>
    );
}
