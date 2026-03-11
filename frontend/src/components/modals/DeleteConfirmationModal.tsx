'use client';

import { Trash2 } from 'lucide-react';
import Button from '@/components/ui/Button';

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
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4" role="dialog" aria-modal="true">
            <div className="w-full max-w-sm bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-9 h-9 bg-red-500/10 rounded-xl flex items-center justify-center border border-red-500/20">
                        <Trash2 className="w-5 h-5 text-red-400" />
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
        </div>
    );
}
