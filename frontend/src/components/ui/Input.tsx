import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface InputBaseProps {
    label?: string;
    error?: string;
}

type InputProps = InputBaseProps &
    React.InputHTMLAttributes<HTMLInputElement>;

type SelectInputProps = InputBaseProps & {
    type: 'select';
} & Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'type'>;

const inputStyles =
    'w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-th-text placeholder-th-text-muted focus:border-primary/30 transition-colors';

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
                        error && 'border-red-500/40',
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
                    'appearance-none cursor-pointer font-medium [&>option]:bg-[#1e293b] [&>option]:text-white',
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
