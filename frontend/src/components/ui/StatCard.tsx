import React from 'react';

interface StatCardProps {
    title: string;
    value: React.ReactNode;
    subtitle?: React.ReactNode;
    icon?: React.ReactNode;
    accentColor?: string;
}

export default function StatCard({ title, value, subtitle, icon, accentColor = 'from-primary/10' }: StatCardProps) {
    return (
        <div className="glass-panel glass-panel-hover p-6 rounded-2xl flex flex-col justify-between group overflow-hidden relative">
            <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${accentColor} to-transparent blur-2xl opacity-0 group-hover:opacity-60 transition-opacity`} />

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-th-text-muted text-[11px] font-semibold uppercase tracking-wider">{title}</h3>
                    {icon && <div className="text-th-text-muted/40 group-hover:text-th-text-muted transition-colors">{icon}</div>}
                </div>

                <p className="text-2xl font-bold text-th-text tracking-tight">{value}</p>
            </div>

            {subtitle && (
                <div className="mt-4 text-sm relative z-10">
                    {subtitle}
                </div>
            )}
        </div>
    );
}
