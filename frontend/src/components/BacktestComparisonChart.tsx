'use client';
import React, { useState, useMemo } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { CHART_COLORS } from '@/lib/constants';
import type { EquityCurvePoint, PriceChangePoint } from '@/types/backtest';

interface Props {
    equityCurve: EquityCurvePoint[];
    priceChanges?: Record<string, PriceChangePoint[]>;
    btcBenchmark?: PriceChangePoint[] | null;
}

const BTC_COLOR = '#f7931a';
const EQUITY_COLOR = '#3b82f6';

export default function BacktestComparisonChart({ equityCurve, priceChanges, btcBenchmark }: Props) {
    // Build list of toggleable lines
    const symbols = useMemo(() => Object.keys(priceChanges || {}), [priceChanges]);
    const hasBtcBenchmark = !!btcBenchmark && btcBenchmark.length > 0;
    const hasBtcInSymbols = symbols.includes('BTC/KRW');

    // Toggle state: equity always on, coins + btc benchmark toggleable
    const [visible, setVisible] = useState<Record<string, boolean>>(() => {
        const init: Record<string, boolean> = { equity: true };
        symbols.forEach(s => { init[s] = true; });
        if (hasBtcBenchmark) init['BTC_BENCH'] = true;
        return init;
    });

    const toggle = (key: string) => {
        if (key === 'equity') return; // equity always visible
        setVisible(prev => ({ ...prev, [key]: !prev[key] }));
    };

    // Merge all data into unified time-series
    const chartData = useMemo(() => {
        if (!equityCurve || equityCurve.length === 0) return [];

        // Equity curve as % change
        const eqFirst = equityCurve[0].value;
        const timeMap = new Map<string, Record<string, number>>();

        equityCurve.forEach(p => {
            const key = p.time;
            if (!timeMap.has(key)) timeMap.set(key, {});
            timeMap.get(key)!.equity = ((p.value / eqFirst) - 1) * 100;
        });

        // Coin price changes
        if (priceChanges) {
            for (const [symbol, points] of Object.entries(priceChanges)) {
                points.forEach(p => {
                    if (!timeMap.has(p.time)) timeMap.set(p.time, {});
                    timeMap.get(p.time)![symbol] = p.value;
                });
            }
        }

        // BTC benchmark
        if (btcBenchmark) {
            btcBenchmark.forEach(p => {
                if (!timeMap.has(p.time)) timeMap.set(p.time, {});
                timeMap.get(p.time)!.BTC_BENCH = p.value;
            });
        }

        // Sort by time and convert
        const sorted = Array.from(timeMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));
        return sorted.map(([time, values]) => ({ time, _zero: 0, ...values }));
    }, [equityCurve, priceChanges, btcBenchmark]);

    if (chartData.length === 0) return null;

    // Color map for symbols
    const symbolColors: Record<string, string> = {};
    symbols.forEach((s, i) => {
        symbolColors[s] = s === 'BTC/KRW' ? BTC_COLOR : CHART_COLORS[i % CHART_COLORS.length];
    });

    const formatTime = (time: string) => {
        const d = new Date(time);
        return `${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')}`;
    };

    const legendItems = [
        { key: 'equity', label: '전략 수익률', color: EQUITY_COLOR, dashed: false },
        ...symbols.map(s => ({
            key: s,
            label: s.split('/')[0],
            color: symbolColors[s],
            dashed: false,
        })),
        ...(hasBtcBenchmark && !hasBtcInSymbols ? [{
            key: 'BTC_BENCH',
            label: 'BTC (벤치마크)',
            color: BTC_COLOR,
            dashed: true,
        }] : []),
    ];

    return (
        <div>
            {/* Custom legend with toggles */}
            <div className="flex flex-wrap gap-3 mb-4">
                {legendItems.map(item => (
                    <button
                        key={item.key}
                        onClick={() => toggle(item.key)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                            visible[item.key]
                                ? 'bg-white/[0.08] text-white'
                                : 'bg-white/[0.02] text-gray-600 line-through'
                        } ${item.key === 'equity' ? 'cursor-default' : 'cursor-pointer hover:bg-white/[0.12]'}`}
                    >
                        <span
                            className="w-3 h-0.5 rounded-full inline-block"
                            style={{
                                backgroundColor: visible[item.key] ? item.color : '#4b5563',
                                ...(item.dashed ? { backgroundImage: `repeating-linear-gradient(90deg, ${item.color} 0, ${item.color} 4px, transparent 4px, transparent 8px)`, backgroundColor: 'transparent' } : {}),
                            }}
                        />
                        {item.label}
                    </button>
                ))}
            </div>

            <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis
                        dataKey="time"
                        tickFormatter={formatTime}
                        stroke="#6b7280"
                        fontSize={11}
                        tickLine={false}
                        interval="preserveStartEnd"
                    />
                    <YAxis
                        stroke="#6b7280"
                        fontSize={11}
                        tickLine={false}
                        tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
                        domain={['auto', 'auto']}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '12px',
                            fontSize: '12px',
                            padding: '10px 14px',
                        }}
                        labelFormatter={(label) => new Date(String(label)).toLocaleString('ko-KR')}
                        formatter={(value, name) => {
                            if (!name || name === '_zero') return [null, null];
                            const num = Number(value);
                            const label = name === 'equity'
                                ? '전략 수익률'
                                : name === 'BTC_BENCH'
                                    ? 'BTC (벤치마크)'
                                    : String(name).split('/')[0];
                            return [`${num > 0 ? '+' : ''}${num.toFixed(2)}%`, label];
                        }}
                    />

                    {/* Zero line */}
                    <Line
                        type="monotone"
                        dataKey="_zero"
                        name="_zero"
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="4 4"
                        legendType="none"
                        isAnimationActive={false}
                    />

                    {/* Equity curve */}
                    {visible.equity && (
                        <Line
                            type="monotone"
                            dataKey="equity"
                            stroke={EQUITY_COLOR}
                            strokeWidth={2.5}
                            dot={false}
                            activeDot={{ r: 4, stroke: EQUITY_COLOR, strokeWidth: 2, fill: '#111827' }}
                            connectNulls
                        />
                    )}

                    {/* Coin price lines */}
                    {symbols.map(symbol => visible[symbol] && (
                        <Line
                            key={symbol}
                            type="monotone"
                            dataKey={symbol}
                            stroke={symbolColors[symbol]}
                            strokeWidth={1.5}
                            dot={false}
                            activeDot={{ r: 3 }}
                            connectNulls
                        />
                    ))}

                    {/* BTC benchmark */}
                    {hasBtcBenchmark && !hasBtcInSymbols && visible.BTC_BENCH && (
                        <Line
                            type="monotone"
                            dataKey="BTC_BENCH"
                            stroke={BTC_COLOR}
                            strokeWidth={1.5}
                            strokeDasharray="6 3"
                            dot={false}
                            activeDot={{ r: 3 }}
                            connectNulls
                        />
                    )}
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
