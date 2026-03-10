import React from 'react';

interface EmptyStateProps {
    icon: React.ReactNode;
    title: string;
    description?: string;
}

export default function EmptyState({ icon, title, description }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 text-gray-700">{icon}</div>
            <p className="text-base font-semibold text-gray-400">{title}</p>
            {description && (
                <p className="text-sm text-gray-600 mt-1">{description}</p>
            )}
        </div>
    );
}
