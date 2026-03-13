'use client';

import { AlertTriangle } from 'lucide-react';
import Button from '@/components/ui/Button';
import ModalWrapper from '@/components/ui/ModalWrapper';

export interface ConfirmationModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    onConfirm: () => void;
    onCancel: () => void;
    loading?: boolean;
    variant?: 'warning' | 'danger';
}

export default function ConfirmationModal({
    isOpen,
    title,
    message,
    confirmLabel = '확인',
    onConfirm,
    onCancel,
    loading = false,
    variant = 'warning',
}: ConfirmationModalProps) {
    const iconColor = variant === 'danger' ? 'text-red-400' : 'text-amber-400';
    const iconBg = variant === 'danger' ? 'bg-red-500/10 border-red-500/20' : 'bg-amber-500/10 border-amber-500/20';
    const buttonVariant = variant === 'danger' ? 'danger' as const : 'primary' as const;

    return (
        <ModalWrapper isOpen={isOpen} maxWidth="max-w-sm">
            <div className="p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${iconBg}`}>
                        <AlertTriangle className={`w-5 h-5 ${iconColor}`} />
                    </div>
                    <h3 className="text-base font-bold text-white">{title}</h3>
                </div>
                <p className="text-sm text-gray-400 mb-6">
                    {message}
                </p>
                <div className="flex gap-3">
                    <Button
                        variant="ghost"
                        size="md"
                        className="flex-1"
                        onClick={onCancel}
                        disabled={loading}
                    >
                        취소
                    </Button>
                    <Button
                        variant={buttonVariant}
                        size="md"
                        className="flex-1"
                        onClick={onConfirm}
                        loading={loading}
                    >
                        {confirmLabel}
                    </Button>
                </div>
            </div>
        </ModalWrapper>
    );
}
