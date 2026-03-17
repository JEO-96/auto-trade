'use client';

import React from 'react';
import { Dialog, DialogContent, DialogHeader } from '@/components/ui/Dialog';

/**
 * Legacy ModalWrapper — delegates to Radix Dialog.
 * Keeps the same external API so existing pages don't break.
 */

interface ModalHeaderProps {
    icon: React.ReactNode;
    title: string;
    titleId?: string;
    onClose: () => void;
}

export function ModalHeader({ icon, title, onClose }: ModalHeaderProps) {
    return <DialogHeader icon={icon} title={title} onClose={onClose} />;
}

interface ModalWrapperProps {
    isOpen: boolean;
    maxWidth?: string;
    children: React.ReactNode;
    ariaLabelledBy?: string;
}

export default function ModalWrapper({ isOpen, maxWidth = 'max-w-md', children, ariaLabelledBy }: ModalWrapperProps) {
    return (
        <Dialog open={isOpen}>
            <DialogContent maxWidth={maxWidth} aria-labelledby={ariaLabelledBy}>
                {children}
            </DialogContent>
        </Dialog>
    );
}
