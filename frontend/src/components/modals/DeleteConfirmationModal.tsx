'use client';

import { Trash2 } from 'lucide-react';
import Button from '@/components/ui/Button';
import ModalWrapper from '@/components/ui/ModalWrapper';

export interface DeleteConfirmationModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    onCancel: () => void;
    loading?: boolean;
}

export default function DeleteConfirmationModal({
    isOpen,
    title,
    message,
    onConfirm,
    onCancel,
    loading = false,
}: DeleteConfirmationModalProps) {
    return (
        <ModalWrapper isOpen={isOpen} maxWidth="max-w-sm">
            <div className="p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 bg-red-500/10 rounded-xl flex items-center justify-center border border-red-500/20">
                        <Trash2 className="w-5 h-5 text-red-400" />
                    </div>
                    <h3 className="text-base font-bold text-th-text">{title}</h3>
                </div>
                <p className="text-sm text-th-text-secondary mb-6">
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
                        variant="danger"
                        size="md"
                        className="flex-1"
                        onClick={onConfirm}
                        loading={loading}
                    >
                        <Trash2 className="w-4 h-4" />
                        삭제
                    </Button>
                </div>
            </div>
        </ModalWrapper>
    );
}
