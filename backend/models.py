from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=True) # Kakao nickname
    hashed_password = Column(String, nullable=True) # Optional for OAuth users
    kakao_id = Column(String, unique=True, index=True, nullable=True)
    kakao_access_token = Column(String, nullable=True) # For "Send to Me" messages
    kakao_refresh_token = Column(String, nullable=True) # For token auto-refresh
    is_active = Column(Boolean, default=False) # Changed to False by default
    is_admin = Column(Boolean, default=False) # 관리자 여부
    created_at = Column(DateTime, default=lambda: datetime.utcnow()) # Added registration time

    bots = relationship("BotConfig", back_populates="owner")
    api_keys = relationship("ExchangeKey", back_populates="owner")

class ExchangeKey(Base):
    __tablename__ = "exchange_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange_name = Column(String, default="upbit")
    api_key_encrypted = Column(String, nullable=False)
    api_secret_encrypted = Column(String, nullable=False)

    owner = relationship("User", back_populates="api_keys")

class BotConfig(Base):
    __tablename__ = "bot_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, default="BTC/KRW")
    timeframe = Column(String, default="1h")
    is_active = Column(Boolean, default=False)
    paper_trading_mode = Column(Boolean, default=True)
    allocated_capital = Column(Float, default=1000000.0)

    strategy_name = Column(String, default="james_pro_stable")

    # James Momentum specific parameters
    rsi_period = Column(Integer, default=14)
    macd_fast = Column(Integer, default=12)
    macd_slow = Column(Integer, default=26)
    volume_ma_period = Column(Integer, default=20)

    owner = relationship("User", back_populates="bots")
    trade_logs = relationship("TradeLog", back_populates="bot")

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bot_configs.id"), index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # 'BUY' or 'SELL'
    price = Column(Float)
    amount = Column(Float)
    pnl = Column(Float, nullable=True) # Realized PnL if it's a SELL
    reason = Column(String) # Entry, Stop Loss, Take Profit
    timestamp = Column(String) # Simplification for SQLite/Postgres compat

    bot = relationship("BotConfig", back_populates="trade_logs")

class OHLCV(Base):
    __tablename__ = "ohlcv_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    timestamp = Column(Float, index=True) # Unix timestamp in ms
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_ohlcv_symbol_tf_ts'),
        Index('ix_ohlcv_symbol_tf_ts', 'symbol', 'timeframe', 'timestamp'),
    )
