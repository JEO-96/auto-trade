import React from 'react';

interface EmptyStateProps {
    icon: React.ReactNode;
    title: string;
    description?: string;
    action?: React.ReactNode;
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 text-th-text-muted/40">{icon}</div>
            <p className="text-base font-semibold text-th-text-secondary">{title}</p>
            {description && (
                <p className="text-sm text-th-text-muted mt-1 max-w-xs">{description}</p>
            )}
            {action && (
                <div className="mt-5">{action}</div>
            )}
        </div>
    );
}
