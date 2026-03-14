from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# -------- User Schemas --------
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    nickname: Optional[str] = None
    is_active: bool
    is_admin: bool = False
    credit_balance: Optional[float] = None
    telegram_chat_id: Optional[str] = None
    notification_trade: bool = True
    notification_bot_status: bool = True
    notification_system: bool = True

    class Config:
        from_attributes = True

# -------- Admin Schemas --------
class AdminDashboardUsers(BaseModel):
    total: int
    active: int
    pending: int
    new_today: int

class AdminDashboardBots(BaseModel):
    total_configs: int
    running_now: int
    live_bots: int
    paper_bots: int

class AdminDashboardTrades(BaseModel):
    total_trades: int
    today_trades: int
    total_pnl: float
    today_pnl: float

class AdminDashboardRevenue(BaseModel):
    total_credit_purchased: float
    total_profit_fees: float
    total_loss_refunds: float
    net_revenue: float

class AdminDashboardSystem(BaseModel):
    active_bot_count: int
    db_connection_ok: bool
    uptime_info: str

class AdminDashboardResponse(BaseModel):
    users: AdminDashboardUsers
    bots: AdminDashboardBots
    trades: AdminDashboardTrades
    revenue: AdminDashboardRevenue
    system: AdminDashboardSystem

class AdminUserResponse(BaseModel):
    id: int
    email: str
    nickname: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# -------- Token Schemas --------
class Token(BaseModel):
    access_token: str
    token_type: str

class KakaoLogin(BaseModel):
    code: str
    redirect_uri: str

class KakaoEmailRequired(BaseModel):
    requires_email: bool = True
    kakao_id: str
    kakao_token: str
    nickname: Optional[str] = None

class KakaoCompleteRegister(BaseModel):
    kakao_id: str
    kakao_token: str
    email: EmailStr
    nickname: Optional[str] = None

# -------- API Key Schemas --------
class ExchangeKeyCreate(BaseModel):
    exchange_name: str
    api_key: str
    api_secret: str

class ExchangeKeyResponse(BaseModel):
    id: int
    exchange_name: str
    api_key_preview: str # We never return the full secret, only preview of the key

    class Config:
        from_attributes = True

class BalanceItem(BaseModel):
    currency: str
    total: float
    free: float
    used: float
    avg_buy_price: Optional[float] = None

class BalanceResponse(BaseModel):
    balances: List[BalanceItem]

# -------- Bot Config Schemas --------
class BotConfigCreate(BaseModel):
    symbol: str
    timeframe: str = "1h"
    strategy_name: str = "momentum_stable"
    paper_trading_mode: bool = True
    allocated_capital: float = 1000000.0
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    volume_ma_period: int = 20


class BotConfigUpdate(BaseModel):
    """봇 설정 수정용 스키마 - 모든 필드 선택적"""
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    strategy_name: Optional[str] = None
    paper_trading_mode: Optional[bool] = None
    allocated_capital: Optional[float] = None
    rsi_period: Optional[int] = None
    macd_fast: Optional[int] = None
    macd_slow: Optional[int] = None
    volume_ma_period: Optional[int] = None


class BotConfigResponse(BaseModel):
    id: int
    symbol: str
    timeframe: str
    strategy_name: Optional[str] = None
    is_active: bool
    paper_trading_mode: bool
    allocated_capital: float
    rsi_period: int
    macd_fast: int
    macd_slow: int
    volume_ma_period: int

    class Config:
        from_attributes = True

# -------- Trade Log Schemas --------
class TradeLogResponse(BaseModel):
    id: int
    bot_id: int
    symbol: str
    side: str
    price: float
    amount: float
    pnl: Optional[float] = None
    reason: str
    timestamp: str

    class Config:
        from_attributes = True

# -------- Backtest Schemas --------
class BacktestRequest(BaseModel):
    symbol: str = "BTC/KRW"
    timeframe: str = "1h"
    strategy_name: str = "james_pro_elite"
    limit: Optional[int] = 1000
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0005  # 수수료율 (기본값: 0.05%)

class PortfolioBacktestRequest(BaseModel):
    symbols: List[str] = ["BTC/KRW"]
    timeframe: str = "1h"
    strategy_name: str = "james_pro_elite"
    limit: Optional[int] = 1000
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0005  # 수수료율 (기본값: 0.05%)

class BacktestTradeResponse(BaseModel):
    symbol: str
    side: str
    price: float
    capital: float
    time: str
    reason: str
    pnl: float

class EquityPoint(BaseModel):
    time: str
    value: float

class BacktestResponse(BaseModel):
    status: str
    task_id: Optional[str] = None
    message: Optional[str] = None
    initial_capital: Optional[float] = None
    final_capital: Optional[float] = None
    total_trades: Optional[int] = None
    trades: Optional[List[BacktestTradeResponse]] = None
    equity_curve: Optional[List[EquityPoint]] = None

class BacktestTaskResponse(BaseModel):
    task_id: str
    status: str  # 'running', 'completed', 'failed'
    progress: float  # 0 to 100
    message: Optional[str] = None
    result: Optional[BacktestResponse] = None


# -------- Backtest History Schemas --------
class BacktestHistoryResponse(BaseModel):
    id: int
    title: Optional[str] = None
    symbols: List[str]
    timeframe: str
    strategy_name: str
    initial_capital: float
    final_capital: Optional[float] = None
    total_trades: Optional[int] = None
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    commission_rate: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BacktestHistoryDetailResponse(BacktestHistoryResponse):
    result_data: Optional[dict] = None

class BacktestHistoryUpdate(BaseModel):
    title: Optional[str] = None


# -------- System Settings Schemas --------
class BacktestSettingsResponse(BaseModel):
    strategy_timeframes: dict[str, List[str]]

class BacktestSettingsUpdate(BaseModel):
    strategy_timeframes: dict[str, List[str]]


# -------- Strategy Visibility --------
class StrategyVisibilityUpdate(BaseModel):
    visibility: dict[str, bool]  # {"steady_compounder_v1": true, ...}


# -------- Active Bots (공개) --------
class ActiveBotPublic(BaseModel):
    nickname: Optional[str] = None
    symbol: str
    timeframe: str
    strategy_name: Optional[str] = None
    paper_trading_mode: bool

class ActiveBotListResponse(BaseModel):
    bots: List[ActiveBotPublic]
    total: int


# -------- Community Schemas --------
class NicknameUpdate(BaseModel):
    nickname: str


class TelegramChatIdUpdate(BaseModel):
    chat_id: str


class NotificationSettings(BaseModel):
    notification_trade: bool = True
    notification_bot_status: bool = True
    notification_system: bool = True


class UserProfileResponse(BaseModel):
    id: int
    nickname: Optional[str] = None
    email: str
    created_at: Optional[datetime] = None
    post_count: int = 0

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    post_type: str  # backtest_share, performance_share, strategy_review, discussion
    title: str
    content: Optional[str] = None
    backtest_data: Optional[dict] = None
    performance_data: Optional[dict] = None
    strategy_name: Optional[str] = None
    timeframe: Optional[str] = None
    rating: Optional[int] = None  # 1-5


class PostResponse(BaseModel):
    id: int
    user_id: int
    author_nickname: Optional[str] = None
    post_type: str
    title: str
    content: Optional[str] = None
    backtest_data: Optional[dict] = None
    performance_data: Optional[dict] = None
    strategy_name: Optional[str] = None
    timeframe: Optional[str] = None
    rating: Optional[int] = None
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    page_size: int


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    user_id: int
    author_nickname: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# -------- Credit Schemas --------
class CreditBalanceResponse(BaseModel):
    balance: float
    total_earned: float
    total_spent: float

    class Config:
        from_attributes = True


class CreditTransactionResponse(BaseModel):
    id: int
    amount: float
    balance_after: float
    tx_type: str
    reference_id: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CreditTransactionListResponse(BaseModel):
    transactions: List[CreditTransactionResponse]
    total: int
    page: int
    page_size: int


class AdminCreditAdjust(BaseModel):
    amount: float
    description: str = ""


class AdminCreditOverview(BaseModel):
    user_id: int
    email: str
    nickname: Optional[str] = None
    balance: float
    total_earned: float
    total_spent: float

    class Config:
        from_attributes = True


# -------- Payment Schemas --------
class PaymentOrderCreate(BaseModel):
    amount: int  # 결제 금액 (원)


class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: int
    credits: int
    toss_client_key: str


class PaymentConfirmRequest(BaseModel):
    payment_key: str
    order_id: str
    amount: int


class PaymentHistoryResponse(BaseModel):
    id: int
    order_id: str
    amount: int
    credits: int
    status: str
    method: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------- Bot Performance Schemas --------
class DailyPnl(BaseModel):
    date: str
    pnl: float
    cumulative_pnl: float

class WeeklyPnl(BaseModel):
    week: str
    pnl: float

class BotPerformanceResponse(BaseModel):
    bot_id: int
    total_pnl: float
    total_trades: int
    win_rate: float
    max_drawdown: float
    daily_pnl: List[DailyPnl]
    weekly_pnl: List[WeeklyPnl]


# -------- Leaderboard Schemas --------
class LeaderboardEntry(BaseModel):
    rank: int
    nickname: str
    strategy_name: str
    strategy_label: str
    total_pnl: float
    win_rate: float
    total_trades: int
    return_rate: float
    is_live: bool


class LeaderboardResponse(BaseModel):
    rankings: List[LeaderboardEntry]
    period: str
    updated_at: datetime


class StrategyRankingEntry(BaseModel):
    strategy_name: str
    strategy_label: str
    avg_return_rate: float
    avg_win_rate: float
    total_users: int
    total_trades: int
    best_return_rate: float


class StrategyRankingsResponse(BaseModel):
    strategies: List[StrategyRankingEntry]


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: int
    user_id: int
    author_nickname: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
