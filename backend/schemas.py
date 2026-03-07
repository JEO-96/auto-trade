from pydantic import BaseModel, EmailStr
from typing import Optional, List

# -------- User Schemas --------
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# -------- Token Schemas --------
class Token(BaseModel):
    access_token: str
    token_type: str

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

# -------- Bot Config Schemas --------
class BotConfigCreate(BaseModel):
    symbol: str
    timeframe: str
    rsi_period: int
    volume_ma_period: int
    allocated_capital: float

class BotConfigResponse(BotConfigCreate):
    id: int
    is_active: bool
    paper_trading_mode: bool
    
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
from pydantic import BaseModel
from typing import List, Optional

class BacktestRequest(BaseModel):
    symbol: str = "BTC/KRW"
    timeframe: str = "1h"
    strategy_name: str = "james_basic"
    limit: Optional[int] = 1000
    start_date: Optional[str] = None # YYYY-MM-DD
    end_date: Optional[str] = None   # YYYY-MM-DD
    initial_capital: float = 1000000.0

class PortfolioBacktestRequest(BaseModel):
    symbols: List[str] = ["BTC/KRW"]
    timeframe: str = "1h"
    strategy_name: str = "james_basic"
    limit: Optional[int] = 1000
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 1000000.0

class BacktestTradeResponse(BaseModel):
    side: str
    price: float
    capital: float
    time: str
    reason: str
    pnl: float

class BacktestResponse(BaseModel):
    status: str
    message: Optional[str] = None
    initial_capital: Optional[float] = None
    final_capital: Optional[float] = None
    total_trades: Optional[int] = None
    trades: Optional[list[BacktestTradeResponse]] = None
