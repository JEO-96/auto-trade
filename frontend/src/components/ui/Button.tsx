import React, { forwardRef } from 'react';

type ButtonVariant = 'primary' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    size?: ButtonSize;
    fullWidth?: boolean;
    loading?: boolean;
    children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
    primary:
        'bg-primary hover:bg-primary-dark text-white font-semibold rounded-xl transition-colors shadow-glow-primary',
    danger:
        'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 font-semibold rounded-xl transition-colors',
    ghost:
        'text-gray-400 hover:text-white hover:bg-white/[0.03] font-semibold rounded-xl transition-colors',
};

const sizeStyles: Record<ButtonSize, string> = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3.5 text-sm',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            variant = 'primary',
            size = 'md',
            fullWidth = false,
            loading = false,
            disabled,
            children,
            className = '',
            ...rest
        },
        ref
    ) => {
        const isDisabled = disabled || loading;

        return (
            <button
                ref={ref}
                disabled={isDisabled}
                className={[
                    'inline-flex items-center justify-center gap-2',
                    variantStyles[variant],
                    sizeStyles[size],
                    fullWidth ? 'w-full' : '',
                    isDisabled ? 'opacity-40 cursor-not-allowed' : '',
                    className,
                ]
                    .filter(Boolean)
                    .join(' ')}
                {...rest}
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
            </button>
        );
    }
);

Button.displayName = 'Button';

export default Button;
