'use client';

import { useTheme } from 'next-themes';
import { Sun, Moon } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function ThemeToggle({ className = '' }: { className?: string }) {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    useEffect(() => setMounted(true), []);

    if (!mounted) {
        return (
            <button className={`w-9 h-9 rounded-xl flex items-center justify-center border border-th-border bg-th-card ${className}`}>
                <div className="w-4 h-4" />
            </button>
        );
    }

    const isDark = theme === 'dark';

    return (
        <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            className={`w-9 h-9 rounded-xl flex items-center justify-center border border-th-border bg-th-card hover:bg-th-hover transition-colors ${className}`}
            aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
        >
            {isDark ? (
                <Sun className="w-4 h-4 text-amber-400" />
            ) : (
                <Moon className="w-4 h-4 text-slate-600" />
            )}
        </button>
    );
}
