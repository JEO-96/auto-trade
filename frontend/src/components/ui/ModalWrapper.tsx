'use client';

import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalHeaderProps {
    icon: React.ReactNode;
    title: string;
    titleId?: string;
    onClose: () => void;
}

export function ModalHeader({ icon, title, onClose }: ModalHeaderProps) {
    return (
        <div className="flex items-center justify-between p-6 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
                {icon}
                {title && (
                    <h2 className="text-base font-bold text-white">{title}</h2>
                )}
            </div>
            <button
                onClick={onClose}
                aria-label="닫기"
                className="text-gray-500 hover:text-gray-300 transition-colors rounded-lg p-1"
            >
                <X className="w-5 h-5" />
            </button>
        </div>
    );
}

interface ModalWrapperProps {
    isOpen: boolean;
    maxWidth?: string;
    children: React.ReactNode;
    ariaLabelledBy?: string;
}

export default function ModalWrapper({ isOpen, maxWidth = 'max-w-md', children }: ModalWrapperProps) {
    // Lock body scroll when modal is open
    useEffect(() => {
        if (!isOpen) return;
        const original = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => { document.body.style.overflow = original; };
    }, [isOpen]);

    if (!isOpen) return null;

    // Use portal to render at document body level
    if (typeof document === 'undefined') return null;

    return createPortal(
        <>
            {/* Overlay */}
            <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" />
            {/* Scroll container - this is the key: a simple fixed div with overflow-y auto */}
            <div
                className="fixed inset-0 z-50 overflow-y-auto"
                style={{ WebkitOverflowScrolling: 'touch' }}
            >
                <div className="flex items-center justify-center min-h-full px-4 py-4">
                    <div className={cn('w-full bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl', maxWidth)}>
                        {children}
                    </div>
                </div>
            </div>
        </>,
        document.body
    );
}
