import api from '@/lib/api';
import type { CreditBalance, CreditTransactionList } from '@/types/user';

export async function getMyCredits(): Promise<CreditBalance> {
    const res = await api.get<CreditBalance>('/credits/');
    return res.data;
}

export async function getCreditHistory(
    page: number = 1,
    pageSize: number = 20,
): Promise<CreditTransactionList> {
    const res = await api.get<CreditTransactionList>('/credits/history', {
        params: { page, page_size: pageSize },
    });
    return res.data;
}

export interface PaymentOrderResponse {
    order_id: string;
    amount: number;
    credits: number;
    toss_client_key: string;
}

export async function createPaymentOrder(amount: number): Promise<PaymentOrderResponse> {
    const res = await api.post<PaymentOrderResponse>('/credits/payment/order', { amount });
    return res.data;
}

export async function confirmPayment(
    paymentKey: string,
    orderId: string,
    amount: number,
): Promise<CreditBalance> {
    const res = await api.post<CreditBalance>('/credits/payment/confirm', {
        payment_key: paymentKey,
        order_id: orderId,
        amount,
    });
    return res.data;
}
