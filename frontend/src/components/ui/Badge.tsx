import React from 'react';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps {
    variant: BadgeVariant;
    children: React.ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
    success: 'bg-secondary/10 text-secondary',
    warning: 'bg-amber-500/10 text-amber-400',
    danger: 'bg-red-500/10 text-red-400',
    info: 'bg-primary/10 text-primary',
};

export default function Badge({ variant, children }: BadgeProps) {
    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold ${variantStyles[variant]}`}
        >
            {children}
        </span>
    );
}
