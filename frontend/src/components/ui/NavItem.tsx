"use client";
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItemProps {
    href: string;
    icon: React.ReactNode;
    label: string;
}

export default function NavItem({ href, icon, label }: NavItemProps) {
    const pathname = usePathname();
    const isActive = pathname === href || (pathname?.startsWith(`${href}/`) && href !== '/dashboard');

    return (
        <Link href={href} className={`group relative flex items-center gap-3 px-6 py-4 rounded-2xl transition-all duration-300 overflow-hidden ${isActive
            ? 'bg-white/5 text-white'
            : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}>
            {/* Active Indicator */}
            {isActive && (
                <div className="absolute left-0 top-1/4 w-1 h-1/2 bg-primary rounded-full shadow-glow-primary" />
            )}

            <div className={`transition-transform duration-300 group-hover:scale-110 ${isActive ? 'text-primary' : ''}`}>
                {icon}
            </div>
            <span className={`text-sm font-bold tracking-tight transition-all ${isActive ? 'translate-x-1' : ''}`}>
                {label}
            </span>

            {/* Hover Background Accent */}
            <div className={`absolute inset-0 bg-gradient-to-r from-primary/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100 ${isActive ? 'opacity-100' : ''}`} />
        </Link>
    );
}

