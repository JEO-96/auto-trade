'use client';

import { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronUp } from 'lucide-react';

interface SymbolPickerProps {
    symbols: string[];
    selected: string[];
    pinnedCount?: number;
    onChange: (selected: string[]) => void;
    label?: string;
}

const INITIAL_VISIBLE = 12;

export default function SymbolPicker({
    symbols,
    selected,
    pinnedCount = 12,
    onChange,
    label = '거래 심볼',
}: SymbolPickerProps) {
    const [search, setSearch] = useState('');
    const [expanded, setExpanded] = useState(false);

    const filtered = useMemo(() => {
        if (!search.trim()) return symbols;
        const q = search.trim().toUpperCase();
        return symbols.filter(s => s.replace('/KRW', '').includes(q));
    }, [symbols, search]);

    const isSearching = search.trim().length > 0;
    const visibleSymbols = isSearching || expanded ? filtered : filtered.slice(0, INITIAL_VISIBLE);
    const hasMore = !isSearching && !expanded && filtered.length > INITIAL_VISIBLE;

    const toggle = (symbol: string) => {
        onChange(
            selected.includes(symbol)
                ? selected.filter(s => s !== symbol)
                : [...selected, symbol]
        );
    };

    return (
        <div>
            <label className="text-xs text-th-text-muted font-medium mb-2 block">
                {label} <span className="text-th-text-muted">&mdash; {selected.length}개 선택</span>
            </label>

            {/* 검색 */}
            <div className="relative mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-th-text-muted" />
                <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="코인 검색 (예: BTC, SOL)"
                    className="w-full pl-8 pr-3 py-2 rounded-lg bg-th-input border border-th-border text-th-text text-xs placeholder-th-text-muted focus:border-primary/30 transition-colors"
                />
            </div>

            {/* 심볼 그리드 */}
            <div className="grid grid-cols-3 gap-1.5 max-h-56 overflow-y-auto pr-1">
                {visibleSymbols.map((s, idx) => {
                    const isSelected = selected.includes(s);
                    const isPinned = !isSearching && idx < pinnedCount;
                    return (
                        <button
                            key={s}
                            type="button"
                            onClick={() => toggle(s)}
                            className={`py-2 rounded-lg text-xs font-semibold transition-all border ${
                                isSelected
                                    ? 'bg-primary/10 border-primary/30 text-primary'
                                    : isPinned
                                        ? 'bg-th-card border-th-border text-th-text-secondary hover:border-primary/20'
                                        : 'bg-th-card border-th-border-light text-th-text-muted hover:border-th-border'
                            }`}
                        >
                            {s.replace('/KRW', '')}
                        </button>
                    );
                })}
            </div>

            {/* 더보기 / 접기 */}
            {hasMore && (
                <button
                    type="button"
                    onClick={() => setExpanded(true)}
                    className="mt-2 w-full py-1.5 text-xs text-th-text-muted hover:text-th-text-secondary transition-colors flex items-center justify-center gap-1"
                >
                    <ChevronDown className="w-3.5 h-3.5" />
                    {filtered.length - INITIAL_VISIBLE}개 더보기
                </button>
            )}
            {expanded && !isSearching && (
                <button
                    type="button"
                    onClick={() => setExpanded(false)}
                    className="mt-2 w-full py-1.5 text-xs text-th-text-muted hover:text-th-text-secondary transition-colors flex items-center justify-center gap-1"
                >
                    <ChevronUp className="w-3.5 h-3.5" />
                    접기
                </button>
            )}

            {filtered.length === 0 && (
                <p className="text-xs text-th-text-muted text-center py-4">검색 결과가 없습니다</p>
            )}
        </div>
    );
}
