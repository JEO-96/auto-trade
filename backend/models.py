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
    telegram_chat_id = Column(String, nullable=True) # 텔레그램 알림용 chat_id
    notification_trade = Column(Boolean, default=True)       # 매매 체결 알림
    notification_bot_status = Column(Boolean, default=True)  # 봇 시작/정지 알림
    notification_system = Column(Boolean, default=True)      # 시스템/공지 알림
    notification_interval = Column(String, default="realtime")  # 정기 피드백 주기: realtime, 4h, 12h, daily
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False) # 관리자 여부
    created_at = Column(DateTime, default=lambda: datetime.utcnow()) # Added registration time

    bots = relationship("BotConfig", back_populates="owner")
    api_keys = relationship("ExchangeKey", back_populates="owner")
    posts = relationship("CommunityPost", back_populates="author")

class ExchangeKey(Base):
    __tablename__ = "exchange_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exchange_name = Column(String, default="upbit")
    api_key_encrypted = Column(String, nullable=False)
    api_secret_encrypted = Column(String, nullable=False)
    passphrase_encrypted = Column(String, nullable=True)  # OKX 등 passphrase 필요 거래소

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

    exchange_name = Column(String, default="upbit")  # 거래소 선택 (upbit, bithumb)
    strategy_name = Column(String, default="james_pro_stable")
    custom_strategy_id = Column(Integer, ForeignKey("user_strategies.id"), nullable=True)

    # James Momentum specific parameters
    rsi_period = Column(Integer, default=14)
    macd_fast = Column(Integer, default=12)
    macd_slow = Column(Integer, default=26)
    volume_ma_period = Column(Integer, default=20)

    owner = relationship("User", back_populates="bots")
    trade_logs = relationship("TradeLog", back_populates="bot")
    custom_strategy = relationship("UserStrategy")

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
    market = Column(String, default="crypto", nullable=False, index=True)  # 'crypto' | 'stock'
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    timestamp = Column(Float, index=True) # Unix timestamp in ms
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    __table_args__ = (
        UniqueConstraint('market', 'symbol', 'timeframe', 'timestamp', name='uq_ohlcv_market_symbol_tf_ts'),
        Index('ix_ohlcv_market_symbol_tf_ts', 'market', 'symbol', 'timeframe', 'timestamp'),
    )


class BacktestHistory(Base):
    __tablename__ = "backtest_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)  # 사용자 지정 제목
    symbols = Column(String, nullable=False)  # JSON array string e.g. '["BTC/KRW"]'
    timeframe = Column(String, nullable=False)
    strategy_name = Column(String, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    result_data = Column(String, nullable=True)  # Full result JSON (trades, equity_curve)
    status = Column(String, default="running")  # running, completed, failed
    start_date = Column(String, nullable=True)  # YYYY-MM-DD
    end_date = Column(String, nullable=True)  # YYYY-MM-DD
    commission_rate = Column(Float, nullable=True)  # 수수료율 (소수)
    custom_params = Column(String, nullable=True)  # 커스텀 튜닝 파라미터 JSON
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    owner = relationship("User")


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_type = Column(String, nullable=False, index=True)  # backtest_share, performance_share, strategy_review, discussion
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    backtest_data = Column(String, nullable=True)  # JSON string
    performance_data = Column(String, nullable=True)  # JSON string
    strategy_name = Column(String, nullable=True)
    timeframe = Column(String, nullable=True)  # e.g., 1h, 4h, 1d for strategy_review
    rating = Column(Integer, nullable=True)  # 1-5 for strategy_review
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())
    is_deleted = Column(Boolean, default=False)

    author = relationship("User", back_populates="posts")
    comments = relationship("PostComment", back_populates="post")
    likes = relationship("PostLike", back_populates="post")


class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    is_deleted = Column(Boolean, default=False)

    post = relationship("CommunityPost", back_populates="comments")
    author = relationship("User")


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    post = relationship("CommunityPost", back_populates="likes")

    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_post_like_user'),
    )


class ActivePosition(Base):
    """봇이 보유 중인 포지션 (서버 재시작 시 복구용)"""
    __tablename__ = "active_positions"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bot_configs.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    position_amount = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    bot = relationship("BotConfig")

    __table_args__ = (
        UniqueConstraint('bot_id', 'symbol', name='uq_active_position_bot_symbol'),
    )


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)  # JSON string


class UserStrategy(Base):
    """사용자 커스텀 전략 (백테스트 파라미터 저장)"""
    __tablename__ = "user_strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    base_strategy_name = Column(String, nullable=False)
    custom_params = Column(String, nullable=False)  # JSON
    backtest_history_id = Column(Integer, ForeignKey("backtest_history.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    is_deleted = Column(Boolean, default=False)

    owner = relationship("User")
    source_backtest = relationship("BacktestHistory")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_strategy_name'),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), index=True)

    author = relationship("User")
