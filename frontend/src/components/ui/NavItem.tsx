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
    const isActive = pathname === href || pathname?.startsWith(`${href}/`) && href !== '/dashboard';

    return (
        <Link href={href} className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
            ? 'bg-primary/10 text-primary border border-primary/20 shadow-[inset_0_0_15px_rgba(59,130,246,0.1)]'
            : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
            }`}>
            {icon}
            <span className="font-medium">{label}</span>
        </Link>
    );
}
