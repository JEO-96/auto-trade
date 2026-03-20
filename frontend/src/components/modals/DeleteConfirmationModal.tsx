'use client';

import { Trash2 } from 'lucide-react';
import ConfirmationModal from './ConfirmationModal';

export interface DeleteConfirmationModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    onCancel: () => void;
    loading?: boolean;
}

export default function DeleteConfirmationModal(props: DeleteConfirmationModalProps) {
    return (
        <ConfirmationModal
            {...props}
            variant="danger"
            confirmLabel="삭제"
            icon={<Trash2 className="w-5 h-5 text-red-400" />}
        />
    );
}
