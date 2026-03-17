'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { ArrowLeft, Send, User as UserIcon } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import Button from '@/components/ui/Button';
import { getChatMessages, sendChatMessage } from '@/lib/api/community';
import { useAuth } from '@/contexts/AuthContext';
import { formatDate } from '@/lib/utils';
import type { ChatMessage } from '@/types/community';

const POLL_INTERVAL_MS = 3000;

function formatTime(dateString: string): string {
    const d = new Date(dateString);
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function shouldShowDateSeparator(current: string, prev?: string): boolean {
    if (!prev) return true;
    const d1 = new Date(current).toDateString();
    const d2 = new Date(prev).toDateString();
    return d1 !== d2;
}

export default function ChatPage() {
    const { user } = useAuth();
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const lastIdRef = useRef<number>(0);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const isAtBottomRef = useRef(true);

    const scrollToBottom = useCallback(() => {
        if (isAtBottomRef.current) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, []);

    const handleScroll = useCallback(() => {
        const el = containerRef.current;
        if (!el) return;
        isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    }, []);

    const fetchMessages = useCallback(async (initial = false) => {
        try {
            const afterId = initial ? undefined : lastIdRef.current || undefined;
            const newMessages = await getChatMessages(afterId);
            if (newMessages.length > 0) {
                if (initial) {
                    setMessages(newMessages);
                } else {
                    setMessages(prev => [...prev, ...newMessages]);
                }
                lastIdRef.current = newMessages[newMessages.length - 1].id;
                setTimeout(scrollToBottom, 100);
            }
        } catch (err) {
            console.error('채팅 메시지 로드 실패', err);
        } finally {
            if (initial) setLoading(false);
        }
    }, [scrollToBottom]);

    useEffect(() => {
        fetchMessages(true);
    }, [fetchMessages]);

    useEffect(() => {
        const interval = setInterval(() => fetchMessages(false), POLL_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [fetchMessages]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;
        setSending(true);
        try {
            const msg = await sendChatMessage(input.trim());
            setMessages(prev => [...prev, msg]);
            lastIdRef.current = msg.id;
            setInput('');
            isAtBottomRef.current = true;
            setTimeout(scrollToBottom, 100);
        } catch (err) {
            console.error('메시지 전송 실패', err);
        } finally {
            setSending(false);
        }
    };

    return (
        <PageContainer maxWidth="max-w-3xl">
            <Link
                href="/dashboard/community"
                className="inline-flex items-center gap-1.5 text-xs text-th-text-muted hover:text-th-text transition-colors mb-4"
            >
                <ArrowLeft className="w-3.5 h-3.5" />
                커뮤니티로 돌아가기
            </Link>

            <div className="glass-panel rounded-2xl flex flex-col" style={{ height: 'calc(100vh - 180px)' }}>
                {/* Header */}
                <div className="px-5 py-4 border-b border-th-border-light shrink-0">
                    <h1 className="text-base font-bold text-th-text">실시간 채팅</h1>
                    <p className="text-[11px] text-th-text-muted">트레이더들과 실시간으로 대화하세요</p>
                </div>

                {/* Messages */}
                {loading ? (
                    <div className="flex-1 flex items-center justify-center">
                        <LoadingSpinner message="채팅 불러오는 중..." />
                    </div>
                ) : (
                    <div
                        ref={containerRef}
                        onScroll={handleScroll}
                        className="flex-1 overflow-y-auto px-5 py-4 space-y-1"
                    >
                        {messages.length === 0 ? (
                            <p className="text-center text-th-text-muted text-xs py-10">아직 메시지가 없습니다. 첫 메시지를 보내보세요!</p>
                        ) : (
                            messages.map((msg, idx) => {
                                const isMe = user?.id === msg.user_id;
                                const prevMsg = idx > 0 ? messages[idx - 1] : undefined;
                                const showDate = shouldShowDateSeparator(msg.created_at, prevMsg?.created_at);
                                const showAuthor = !isMe && (!prevMsg || prevMsg.user_id !== msg.user_id || showDate);

                                return (
                                    <div key={msg.id}>
                                        {showDate && (
                                            <div className="flex items-center gap-3 my-4">
                                                <div className="flex-1 h-px bg-th-border-light" />
                                                <span className="text-[10px] text-th-text-muted font-medium">
                                                    {formatDate(msg.created_at)}
                                                </span>
                                                <div className="flex-1 h-px bg-th-border-light" />
                                            </div>
                                        )}
                                        <div className={`flex ${isMe ? 'justify-end' : 'justify-start'} mb-0.5`}>
                                            <div className={`max-w-[75%] ${isMe ? 'order-2' : ''}`}>
                                                {showAuthor && (
                                                    <div className="flex items-center gap-1.5 mb-1 ml-1">
                                                        <div className="w-4 h-4 rounded bg-th-border flex items-center justify-center">
                                                            <UserIcon className="w-2.5 h-2.5 text-th-text-muted" />
                                                        </div>
                                                        <span className="text-[10px] text-th-text-muted font-semibold">
                                                            {msg.author_nickname ?? '익명'}
                                                        </span>
                                                    </div>
                                                )}
                                                <div className={`group flex items-end gap-1.5 ${isMe ? 'flex-row-reverse' : ''}`}>
                                                    <div
                                                        className={`px-3.5 py-2 rounded-2xl text-sm leading-relaxed ${
                                                            isMe
                                                                ? 'bg-primary/20 text-white rounded-br-md'
                                                                : 'bg-th-card text-th-text-secondary rounded-bl-md'
                                                        }`}
                                                    >
                                                        {msg.content}
                                                    </div>
                                                    <span className="text-[9px] text-th-text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                                                        {formatTime(msg.created_at)}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                )}

                {/* Input */}
                <form onSubmit={handleSend} className="px-5 py-3 border-t border-th-border-light shrink-0">
                    <div className="flex items-center gap-2">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="메시지를 입력하세요..."
                            maxLength={500}
                            className="flex-1 bg-th-card border border-th-border rounded-xl px-4 py-2.5 text-sm text-th-text placeholder-th-text-muted focus:border-primary/30 transition-colors"
                        />
                        <Button type="submit" size="sm" loading={sending} disabled={!input.trim()}>
                            <Send className="w-4 h-4" />
                        </Button>
                    </div>
                </form>
            </div>
        </PageContainer>
    );
}
