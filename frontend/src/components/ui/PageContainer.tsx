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
        <div className={`px-5 pt-6 pb-6 lg:p-8 ${maxWidth} mx-auto animate-fade-in-up`}>
            {children}
        </div>
    );
}
