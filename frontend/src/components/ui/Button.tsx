import React, { forwardRef } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
    'inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none',
    {
        variants: {
            variant: {
                primary:
                    'bg-primary hover:bg-primary-dark text-white shadow-glow-primary hover:shadow-[0_4px_16px_rgba(59,130,246,0.35)] active:scale-[0.98]',
                danger:
                    'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/30 active:scale-[0.98]',
                ghost:
                    'text-gray-400 hover:text-white hover:bg-white/[0.03] active:bg-white/[0.06] [.light_&]:text-th-text-secondary [.light_&]:hover:text-th-text [.light_&]:hover:bg-th-hover [.light_&]:active:bg-th-border',
                outline:
                    'border border-white/[0.08] text-gray-400 hover:text-white hover:bg-white/[0.04] hover:border-white/[0.12] active:scale-[0.98] [.light_&]:border-th-border [.light_&]:text-th-text-secondary [.light_&]:hover:text-th-text [.light_&]:hover:bg-th-hover [.light_&]:hover:border-th-border',
                secondary:
                    'bg-secondary/10 text-secondary hover:bg-secondary/20 border border-secondary/20 active:scale-[0.98]',
            },
            size: {
                sm: 'px-3 py-1.5 text-xs',
                md: 'px-4 py-2.5 text-sm',
                lg: 'px-6 py-3.5 text-sm',
                icon: 'h-9 w-9',
            },
        },
        defaultVariants: {
            variant: 'primary',
            size: 'md',
        },
    }
);

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
        VariantProps<typeof buttonVariants> {
    asChild?: boolean;
    fullWidth?: boolean;
    loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            className,
            variant,
            size,
            asChild = false,
            fullWidth = false,
            loading = false,
            disabled,
            children,
            ...props
        },
        ref
    ) => {
        const Comp = asChild ? Slot : 'button';
        const isDisabled = disabled || loading;

        return (
            <Comp
                ref={ref}
                disabled={isDisabled}
                className={cn(
                    buttonVariants({ variant, size }),
                    fullWidth && 'w-full',
                    className
                )}
                {...props}
            >
                {loading ? (
                    <>
                        <span
                            className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"
                            aria-hidden="true"
                        />
                        <span className="sr-only">로딩 중</span>
                        {children}
                    </>
                ) : (
                    children
                )}
            </Comp>
        );
    }
);

Button.displayName = 'Button';

export { buttonVariants };
export default Button;
