from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

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
    bot_id = Column(Integer, ForeignKey("bot_configs.id"))
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

    # Note: In a real app, you'd add a UniqueConstraint(symbol, timeframe, timestamp)
    # to avoid duplicates during bulk inserts.
