'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
    id: number;
    type: ToastType;
    message: string;
}

interface ToastContextValue {
    toast: {
        success: (message: string) => void;
        error: (message: string) => void;
        warning: (message: string) => void;
        info: (message: string) => void;
    };
}

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 0;

const ICON_MAP: Record<ToastType, typeof CheckCircle2> = {
    success: CheckCircle2,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
};

const STYLE_MAP: Record<ToastType, string> = {
    success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    error: 'border-red-500/30 bg-red-500/10 text-red-400',
    warning: 'border-amber-500/30 bg-amber-500/10 text-amber-400',
    info: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: number) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const addToast = useCallback((type: ToastType, message: string) => {
        const id = ++nextId;
        setToasts(prev => [...prev, { id, type, message }]);
        setTimeout(() => removeToast(id), 4000);
    }, [removeToast]);

    const toast = {
        success: (message: string) => addToast('success', message),
        error: (message: string) => addToast('error', message),
        warning: (message: string) => addToast('warning', message),
        info: (message: string) => addToast('info', message),
    };

    return (
        <ToastContext.Provider value={{ toast }}>
            {children}
            {/* Toast Container */}
            <div
                className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
                aria-live="polite"
            >
                {toasts.map(t => (
                    <ToastItem key={t.id} toast={t} onDismiss={removeToast} />
                ))}
            </div>
        </ToastContext.Provider>
    );
}

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
    const [show, setShow] = useState(false);
    const Icon = ICON_MAP[t.type];

    useEffect(() => {
        requestAnimationFrame(() => setShow(true));
    }, []);

    const handleDismiss = () => {
        setShow(false);
        setTimeout(() => onDismiss(t.id), 200);
    };

    return (
        <div
            role="alert"
            className={[
                'pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-lg max-w-sm transition-all duration-200',
                STYLE_MAP[t.type],
                show ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4',
            ].join(' ')}
        >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="text-sm font-medium flex-1">{t.message}</span>
            <button
                onClick={handleDismiss}
                className="shrink-0 p-0.5 rounded hover:bg-white/10 transition-colors"
                aria-label="닫기"
            >
                <X className="w-3.5 h-3.5" />
            </button>
        </div>
    );
}

export function useToast(): ToastContextValue['toast'] {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error('useToast must be used within ToastProvider');
    return ctx.toast;
}
