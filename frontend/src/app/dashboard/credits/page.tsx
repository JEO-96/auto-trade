'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Coins, TrendingUp, TrendingDown, Gift, Shield, ChevronLeft, ChevronRight, Plus, CreditCard, Wallet } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer';
import { getMyCredits, getCreditHistory, createPaymentOrder, confirmPayment } from '@/lib/api';
import type { CreditBalance, CreditTransaction } from '@/types/user';

const TX_TYPE_MAP: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
    signup_bonus: { label: '가입 보너스', icon: <Gift className="w-4 h-4" />, color: 'text-purple-400' },
    profit_fee: { label: '수익 수수료', icon: <TrendingDown className="w-4 h-4" />, color: 'text-red-400' },
    loss_refund: { label: '손실 환불', icon: <TrendingUp className="w-4 h-4" />, color: 'text-green-400' },
    admin_adjust: { label: '관리자 조정', icon: <Shield className="w-4 h-4" />, color: 'text-yellow-400' },
    purchase: { label: '크레딧 충전', icon: <CreditCard className="w-4 h-4" />, color: 'text-blue-400' },
};

const PRESET_AMOUNTS = [5000, 10000, 30000, 50000, 100000];

export default function CreditsPage() {
    const [balance, setBalance] = useState<CreditBalance | null>(null);
    const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [showChargeModal, setShowChargeModal] = useState(false);
    const [chargeAmount, setChargeAmount] = useState<number>(10000);
    const [customAmount, setCustomAmount] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [chargeError, setChargeError] = useState('');
    const pageSize = 15;

    // 토스 결제 처리 완료를 위한 URL 파라미터 체크
    const hasCheckedPayment = useRef(false);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [b, h] = await Promise.all([
                getMyCredits(),
                getCreditHistory(page, pageSize),
            ]);
            setBalance(b);
            setTransactions(h.transactions);
            setTotal(h.total);
        } catch (err) {
            console.error('Failed to fetch credits:', err);
        } finally {
            setLoading(false);
        }
    }, [page]);

    useEffect(() => { fetchData(); }, [fetchData]);

    // 토스 결제 성공 콜백 처리 (리다이렉트 방식)
    useEffect(() => {
        if (hasCheckedPayment.current) return;
        hasCheckedPayment.current = true;

        const params = new URLSearchParams(window.location.search);
        const paymentKey = params.get('paymentKey');
        const orderId = params.get('orderId');
        const amount = params.get('amount');

        if (paymentKey && orderId && amount) {
            setIsProcessing(true);
            confirmPayment(paymentKey, orderId, parseInt(amount))
                .then(() => {
                    fetchData();
                    // URL 파라미터 제거
                    window.history.replaceState({}, '', '/dashboard/credits');
                })
                .catch((err) => {
                    console.error('Payment confirm failed:', err);
                    setChargeError(err.response?.data?.detail || '결제 승인에 실패했습니다.');
                })
                .finally(() => setIsProcessing(false));
        }
    }, [fetchData]);

    const handleCharge = async () => {
        const amount = customAmount ? parseInt(customAmount) : chargeAmount;
        if (!amount || amount < 1000) {
            setChargeError('최소 충전 금액은 1,000원입니다.');
            return;
        }
        if (amount > 1000000) {
            setChargeError('최대 충전 금액은 1,000,000원입니다.');
            return;
        }

        setIsProcessing(true);
        setChargeError('');

        try {
            const order = await createPaymentOrder(amount);

            // 토스페이먼츠 SDK 로드 및 결제 요청
            const { loadTossPayments } = await import('@tosspayments/tosspayments-sdk');
            const toss = await loadTossPayments(order.toss_client_key);
            const payment = toss.payment({ customerKey: `user_${Date.now()}` });

            await payment.requestPayment({
                method: 'CARD',
                amount: { currency: 'KRW', value: order.amount },
                orderId: order.order_id,
                orderName: `크레딧 ${order.credits.toLocaleString()}개 충전`,
                successUrl: `${window.location.origin}/dashboard/credits?`,
                failUrl: `${window.location.origin}/dashboard/credits?payment=fail`,
            });
        } catch (err: unknown) {
            const error = err as { code?: string; message?: string; response?: { data?: { detail?: string } } };
            if (error.code === 'USER_CANCEL') {
                // 사용자가 결제 취소
            } else {
                setChargeError(error.response?.data?.detail || error.message || '결제 요청에 실패했습니다.');
            }
        } finally {
            setIsProcessing(false);
        }
    };

    const totalPages = Math.ceil(total / pageSize);
    const selectedAmount = customAmount ? parseInt(customAmount) || 0 : chargeAmount;

    return (
        <PageContainer>
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white">크레딧</h1>
                    <p className="text-sm text-gray-400 mt-1">1원 = 1크레딧 | 실매매 수익의 10% 수수료, 손실 시 10% 환불</p>
                </div>
                <button
                    onClick={() => { setShowChargeModal(true); setChargeError(''); }}
                    className="flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 text-white font-semibold rounded-xl transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    충전하기
                </button>
            </div>

            {/* 결제 처리 중 오버레이 */}
            {isProcessing && (
                <div className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-center justify-center">
                    <div className="bg-[#0f172a] border border-white/[0.08] rounded-2xl p-8 text-center">
                        <div className="w-10 h-10 border-3 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                        <p className="text-white font-semibold">결제 처리 중...</p>
                    </div>
                </div>
            )}

            {/* 잔액 카드 */}
            {balance && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div className="bg-surface/60 backdrop-blur-xl border border-white/[0.06] rounded-2xl p-6">
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">
                                <Coins className="w-5 h-5 text-primary" />
                            </div>
                            <span className="text-sm text-gray-400">현재 잔액</span>
                        </div>
                        <p className={`text-3xl font-bold ${balance.balance > 0 ? 'text-white' : 'text-red-400'}`}>
                            {balance.balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">크레딧</p>
                    </div>

                    <div className="bg-surface/60 backdrop-blur-xl border border-white/[0.06] rounded-2xl p-6">
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center border border-green-500/20">
                                <TrendingUp className="w-5 h-5 text-green-400" />
                            </div>
                            <span className="text-sm text-gray-400">총 획득</span>
                        </div>
                        <p className="text-2xl font-bold text-green-400">
                            +{balance.total_earned.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </p>
                    </div>

                    <div className="bg-surface/60 backdrop-blur-xl border border-white/[0.06] rounded-2xl p-6">
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 bg-red-500/10 rounded-xl flex items-center justify-center border border-red-500/20">
                                <TrendingDown className="w-5 h-5 text-red-400" />
                            </div>
                            <span className="text-sm text-gray-400">총 사용</span>
                        </div>
                        <p className="text-2xl font-bold text-red-400">
                            -{balance.total_spent.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </p>
                    </div>
                </div>
            )}

            {/* 거래 내역 */}
            <div className="bg-surface/60 backdrop-blur-xl border border-white/[0.06] rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-white/[0.06]">
                    <h2 className="text-lg font-semibold text-white">거래 내역</h2>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : transactions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                        <Coins className="w-10 h-10 mb-3 opacity-30" />
                        <p>거래 내역이 없습니다.</p>
                    </div>
                ) : (
                    <>
                        <div className="divide-y divide-white/[0.04]">
                            {transactions.map((tx) => {
                                const info = TX_TYPE_MAP[tx.tx_type] || {
                                    label: tx.tx_type,
                                    icon: <Coins className="w-4 h-4" />,
                                    color: 'text-gray-400',
                                };
                                const isPositive = tx.amount > 0;
                                return (
                                    <div key={tx.id} className="px-6 py-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors">
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isPositive ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                                            <span className={info.color}>{info.icon}</span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-white">{info.label}</p>
                                            <p className="text-xs text-gray-500 truncate">{tx.description}</p>
                                        </div>
                                        <div className="text-right shrink-0">
                                            <p className={`text-sm font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                                {isPositive ? '+' : ''}{tx.amount.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                                            </p>
                                            <p className="text-xs text-gray-600">
                                                {new Date(tx.created_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                            </p>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {totalPages > 1 && (
                            <div className="flex items-center justify-center gap-4 px-6 py-4 border-t border-white/[0.06]">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <span className="text-sm text-gray-400">{page} / {totalPages}</span>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* 충전 모달 */}
            {showChargeModal && (
                <div
                    className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
                    onClick={() => setShowChargeModal(false)}
                >
                    <div
                        className="bg-[#0f172a] border border-white/[0.08] rounded-2xl w-full max-w-md overflow-hidden"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="px-6 py-5 border-b border-white/[0.06]">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
                                    <Wallet className="w-5 h-5 text-blue-400" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-white">크레딧 충전</h3>
                                    <p className="text-xs text-gray-400">1원 = 1크레딧</p>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 space-y-5">
                            {/* 프리셋 금액 */}
                            <div>
                                <p className="text-sm text-gray-400 mb-3">충전 금액 선택</p>
                                <div className="grid grid-cols-3 gap-2">
                                    {PRESET_AMOUNTS.map((amt) => (
                                        <button
                                            key={amt}
                                            onClick={() => { setChargeAmount(amt); setCustomAmount(''); setChargeError(''); }}
                                            className={`py-3 rounded-xl text-sm font-semibold transition-all ${
                                                !customAmount && chargeAmount === amt
                                                    ? 'bg-primary text-white ring-2 ring-primary/30'
                                                    : 'bg-white/[0.04] text-gray-300 hover:bg-white/[0.08] border border-white/[0.06]'
                                            }`}
                                        >
                                            {amt.toLocaleString()}원
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* 직접 입력 */}
                            <div>
                                <p className="text-sm text-gray-400 mb-2">직접 입력</p>
                                <div className="relative">
                                    <input
                                        type="number"
                                        placeholder="금액을 입력하세요"
                                        value={customAmount}
                                        onChange={(e) => { setCustomAmount(e.target.value); setChargeError(''); }}
                                        min={1000}
                                        max={1000000}
                                        className="w-full px-4 py-3 bg-white/[0.04] border border-white/[0.08] rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                                    />
                                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-gray-500">원</span>
                                </div>
                            </div>

                            {/* 충전 요약 */}
                            {selectedAmount > 0 && (
                                <div className="bg-white/[0.03] rounded-xl p-4 border border-white/[0.06]">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-400">결제 금액</span>
                                        <span className="text-white font-semibold">{selectedAmount.toLocaleString()}원</span>
                                    </div>
                                    <div className="flex justify-between text-sm mt-2">
                                        <span className="text-gray-400">충전 크레딧</span>
                                        <span className="text-primary font-bold">{selectedAmount.toLocaleString()} 크레딧</span>
                                    </div>
                                </div>
                            )}

                            {chargeError && (
                                <p className="text-sm text-red-400">{chargeError}</p>
                            )}
                        </div>

                        <div className="px-6 pb-6 flex gap-3">
                            <button
                                onClick={() => setShowChargeModal(false)}
                                className="flex-1 py-3 rounded-xl text-sm font-semibold bg-white/[0.04] text-gray-300 hover:bg-white/[0.08] border border-white/[0.06] transition-colors"
                            >
                                취소
                            </button>
                            <button
                                onClick={handleCharge}
                                disabled={isProcessing || selectedAmount < 1000}
                                className="flex-1 py-3 rounded-xl text-sm font-semibold bg-primary hover:bg-primary/90 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                            >
                                <CreditCard className="w-4 h-4" />
                                {isProcessing ? '처리 중...' : `${selectedAmount.toLocaleString()}원 결제`}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </PageContainer>
    );
}
