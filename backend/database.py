import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# AWS Lightsail PostgreSQL Connection Info
DB_USER = os.getenv("DB_USER", "dbmasteruser")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

if not DB_PASS or not DB_HOST:
    raise RuntimeError("DB_PASS and DB_HOST must be set as environment variables")

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

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
