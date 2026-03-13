export interface ExchangeKeyPreview {
    id: number;
    exchange_name: string;
    api_key_preview: string;
}

export interface ExchangeKeyCreateRequest {
    exchange_name: string;
    api_key: string;
    api_secret: string;
}

export interface BalanceItem {
    currency: string;
    total: number;
    free: number;
    used: number;
    avg_buy_price: number | null;
}
