'use client';

import { X } from 'lucide-react';

interface ModalHeaderProps {
    icon: React.ReactNode;
    title: string;
    titleId?: string;
    onClose: () => void;
}

export function ModalHeader({ icon, title, titleId, onClose }: ModalHeaderProps) {
    return (
        <div className="flex items-center justify-between p-6 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
                {icon}
                <h2 id={titleId} className="text-base font-bold text-white">{title}</h2>
            </div>
            <button onClick={onClose} aria-label="닫기" className="text-gray-500 hover:text-gray-300 transition-colors">
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

export default function ModalWrapper({ isOpen, maxWidth = 'max-w-md', children, ariaLabelledBy }: ModalWrapperProps) {
    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby={ariaLabelledBy}
        >
            <div className={`w-full ${maxWidth} bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl`}>
                {children}
            </div>
        </div>
    );
}
