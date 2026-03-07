import React from 'react';

interface StatCardProps {
    title: string;
    value: React.ReactNode;
    subtitle?: React.ReactNode;
    icon?: React.ReactNode;
    accentColor?: string; // e.g. 'bg-primary/5', 'bg-emerald-500/5'
}

export default function StatCard({ title, value, subtitle, icon, accentColor = 'bg-primary/5' }: StatCardProps) {
    return (
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden flex flex-col justify-between">
            <div className={`absolute top-0 right-0 w-24 h-24 ${accentColor} rounded-bl-[100px] -z-10`}></div>
            <div>
                <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">{title}</h3>
                <div className="flex items-center gap-2">
                    {icon && <div className="opacity-70">{icon}</div>}
                    <p className="text-2xl font-bold font-mono text-white">{value}</p>
                </div>
            </div>
            {subtitle && (
                <div className="mt-4 text-sm">
                    {subtitle}
                </div>
            )}
        </div>
    );
}
