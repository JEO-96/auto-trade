"use client";
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItemProps {
    href: string;
    icon: React.ReactNode;
    label: string;
}

export default function NavItem({ href, icon, label  }: NavItemProps) {
    const pathname = usePathname();
    const isActive = pathname === href || (pathname?.startsWith(`${href}/`) && href !== '/dashboard');

    return (
        <Link href={href} className={`group relative flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 ${isActive
            ? 'bg-th-border text-th-text'
            : 'text-th-text-muted hover:text-th-text hover:bg-th-hover'
            }`}>
            <div className={`transition-colors ${isActive ? 'text-primary' : ''}`}>
                {icon}
            </div>
            <span className="text-[13px] font-semibold tracking-tight">
                {label}
            </span>

            {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-primary rounded-full" />
            )}
        </Link>
    );
}
