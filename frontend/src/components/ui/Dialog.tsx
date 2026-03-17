'use client';

import React, { forwardRef } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const DialogOverlay = forwardRef<
    React.ElementRef<typeof DialogPrimitive.Overlay>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
    <DialogPrimitive.Overlay
        ref={ref}
        className={cn(
            'fixed inset-0 z-50 bg-th-overlay backdrop-blur-sm',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0',
            className
        )}
        {...props}
    />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = forwardRef<
    React.ElementRef<typeof DialogPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
        maxWidth?: string;
    }
>(({ className, children, maxWidth = 'max-w-md', ...props }, ref) => (
    <DialogPortal>
        <DialogOverlay />
        <DialogPrimitive.Content
            ref={ref}
            className={cn(
                'fixed left-[50%] top-[50%] z-50 w-full translate-x-[-50%] translate-y-[-50%] px-4',
                maxWidth,
                'data-[state=open]:animate-in data-[state=closed]:animate-out',
                'data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0',
                'data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95',
                'data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]',
                'data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%]',
                'duration-200',
                className
            )}
            {...props}
        >
            <div className="bg-[#0d1117] border border-white/[0.08] rounded-2xl shadow-2xl overflow-hidden">
                {children}
            </div>
        </DialogPrimitive.Content>
    </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

function DialogHeader({
    className,
    icon,
    title,
    onClose,
    ...props
}: React.HTMLAttributes<HTMLDivElement> & {
    icon?: React.ReactNode;
    title?: string;
    onClose?: () => void;
}) {
    return (
        <div
            className={cn(
                'flex items-center justify-between p-6 border-b border-white/[0.06]',
                className
            )}
            {...props}
        >
            <div className="flex items-center gap-3">
                {icon}
                {title && (
                    <DialogPrimitive.Title className="text-base font-bold text-white">
                        {title}
                    </DialogPrimitive.Title>
                )}
            </div>
            {onClose ? (
                <button
                    onClick={onClose}
                    aria-label="닫기"
                    className="text-gray-500 hover:text-gray-300 transition-colors rounded-lg p-1"
                >
                    <X className="w-5 h-5" />
                </button>
            ) : (
                <DialogPrimitive.Close className="text-gray-500 hover:text-gray-300 transition-colors rounded-lg p-1">
                    <X className="w-5 h-5" />
                    <span className="sr-only">닫기</span>
                </DialogPrimitive.Close>
            )}
        </div>
    );
}

const DialogFooter = ({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
    <div
        className={cn('flex gap-3 p-6 pt-2', className)}
        {...props}
    />
);

const DialogDescription = DialogPrimitive.Description;

export {
    Dialog,
    DialogPortal,
    DialogOverlay,
    DialogClose,
    DialogTrigger,
    DialogContent,
    DialogHeader,
    DialogFooter,
    DialogDescription,
};
