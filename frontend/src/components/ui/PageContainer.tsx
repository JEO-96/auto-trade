import React from 'react';

interface PageContainerProps {
    children: React.ReactNode;
    maxWidth?: string;
}

export default function PageContainer({
    children,
    maxWidth = 'max-w-7xl',
}: PageContainerProps) {
    return (
        <div className={`p-6 pr-16 lg:p-8 lg:pr-8 ${maxWidth} mx-auto animate-fade-in-up`}>
            {children}
        </div>
    );
}
