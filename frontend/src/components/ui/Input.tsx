import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface InputBaseProps {
    label?: string;
    error?: string;
}

type InputProps = InputBaseProps &
    React.InputHTMLAttributes<HTMLInputElement>;

interface SelectInputProps extends InputBaseProps {
    type: 'select';
    children: React.ReactNode;
    value?: string;
    onChange?: React.ChangeEventHandler<HTMLSelectElement>;
    name?: string;
    className?: string;
}

const inputStyles =
    'w-full bg-th-input border border-th-border rounded-xl px-4 py-3 text-sm text-th-text placeholder-th-text-muted transition-all duration-200 focus:border-primary/40 focus:ring-2 focus:ring-primary/10 focus:outline-none';

const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ label, error, className, id, ...rest }, ref) => {
        const inputId = id || (label ? `input-${label.replace(/\s/g, '-')}` : undefined);

        return (
            <div>
                {label && (
                    <label
                        htmlFor={inputId}
                        className="text-xs text-th-text-muted font-medium mb-1.5 block"
                    >
                        {label}
                    </label>
                )}
                <input
                    ref={ref}
                    id={inputId}
                    className={cn(
                        inputStyles,
                        error && 'border-red-500/40 focus:border-red-500/60 focus:ring-red-500/10',
                        className
                    )}
                    {...rest}
                />
                {error && (
                    <p className="text-xs text-red-400 mt-1.5" role="alert">
                        {error}
                    </p>
                )}
            </div>
        );
    }
);

Input.displayName = 'Input';

export function SelectInput({
    type: _type,
    label,
    error,
    children,
    className = '',
    ...selectProps
}: SelectInputProps) {
    const selectId = label ? `select-${label.replace(/\s/g, '-')}` : undefined;

    return (
        <div>
            {label && (
                <label
                    htmlFor={selectId}
                    className="text-xs text-th-text-muted font-medium mb-1.5 block"
                >
                    {label}
                </label>
            )}
            <select
                id={selectId}
                className={cn(
                    inputStyles,
                    'appearance-none cursor-pointer font-medium [&>option]:bg-[--select-bg] [&>option]:text-th-text',
                    error && 'border-red-500/40',
                    className
                )}
                {...selectProps}
            >
                {children}
            </select>
            {error && (
                <p className="text-xs text-red-400 mt-1.5" role="alert">
                    {error}
                </p>
            )}
        </div>
    );
}

export default Input;
