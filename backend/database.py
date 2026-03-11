import urllib.parse
from sqlalchemy import create_engine
from contextlib import contextmanager
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from settings import settings

# AWS Lightsail PostgreSQL Connection Info
DB_USER = settings.db_user
DB_PASS = settings.db_pass
DB_HOST = settings.db_host
DB_PORT = settings.db_port
DB_NAME = settings.db_name

# URL encoding is required because the password contains special characters ($, [, ^, etc.)
safe_password = urllib.parse.quote_plus(DB_PASS)

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Engine Configuration
# pool_size: number of persistent connections kept open
# max_overflow: extra connections allowed beyond pool_size under load
# pool_timeout: seconds to wait for a connection before raising an error
# pool_recycle: recycle connections after this many seconds (avoids stale connections)
# pool_pre_ping: test connections before use to detect dropped connections
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Context manager for standalone DB session usage (outside FastAPI Depends)
@contextmanager
def get_db_session():
    """Provides a transactional DB session with automatic cleanup.

    Usage:
        with get_db_session() as db:
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
