import React from 'react';

type SpinnerSize = 'sm' | 'md' | 'lg';

interface LoadingSpinnerProps {
    size?: SpinnerSize;
    message?: string;
}

const sizeMap: Record<SpinnerSize, string> = {
    sm: 'w-6 h-6 border',
    md: 'w-10 h-10 border-2',
    lg: 'w-14 h-14 border-2',
};

export default function LoadingSpinner({
    size = 'md',
    message,
}: LoadingSpinnerProps) {
    return (
        <div className="flex flex-col items-center gap-4" role="status">
            <div
                className={`${sizeMap[size]} border-primary/20 border-t-primary rounded-full animate-spin`}
                aria-hidden="true"
            />
            {message && (
                <p className="text-gray-500 text-sm font-medium">{message}</p>
            )}
            <span className="sr-only">{message || '로딩 중...'}</span>
        </div>
    );
}
