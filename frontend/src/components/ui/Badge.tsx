import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
    'inline-flex items-center gap-1 rounded-md text-[10px] font-semibold transition-colors',
    {
        variants: {
            variant: {
                success: 'bg-secondary/10 text-secondary border border-secondary/20',
                warning: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
                danger: 'bg-red-500/10 text-red-400 border border-red-500/20',
                info: 'bg-primary/10 text-primary border border-primary/20',
                default: 'bg-white/[0.06] text-gray-400 [.light_&]:bg-th-border [.light_&]:text-th-text-secondary [.light_&]:border [.light_&]:border-th-border-light',
            },
            size: {
                sm: 'px-1.5 py-0.5',
                md: 'px-2 py-0.5',
                lg: 'px-2.5 py-1',
            },
        },
        defaultVariants: {
            variant: 'default',
            size: 'md',
        },
    }
);

export interface BadgeProps
    extends React.HTMLAttributes<HTMLSpanElement>,
        VariantProps<typeof badgeVariants> {}

export default function Badge({ className, variant, size, ...props }: BadgeProps) {
    return (
        <span className={cn(badgeVariants({ variant, size }), className)} {...props} />
    );
}

export { badgeVariants };
