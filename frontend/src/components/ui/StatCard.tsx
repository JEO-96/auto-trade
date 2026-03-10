import React from 'react';

interface StatCardProps {
    title: string;
    value: React.ReactNode;
    subtitle?: React.ReactNode;
    icon?: React.ReactNode;
    accentColor?: string;
}

export default function StatCard({ title, value, subtitle, icon, accentColor = 'from-primary/20 to-transparent' }: StatCardProps) {
    return (
        <div className="glass-panel glass-panel-hover p-8 rounded-[2rem] flex flex-col justify-between group overflow-hidden relative">
            {/* Background Accent */}
            <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${accentColor} blur-2xl opacity-50 group-hover:opacity-80 transition-opacity`} />

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-gray-400 text-xs font-bold uppercase tracking-[0.1em]">{title}</h3>
                    {icon && <div className="text-white/40 group-hover:text-white/80 transition-colors">{icon}</div>}
                </div>

                <div className="flex items-baseline gap-2">
                    <p className="text-3xl font-extrabold text-white tracking-tight">{value}</p>
                </div>
            </div>

            {subtitle && (
                <div className="mt-6 text-sm font-medium text-gray-500 relative z-10">
                    {subtitle}
                </div>
            )}
        </div>
    );
}

