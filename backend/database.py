import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# AWS Lightsail PostgreSQL Connection Info
DB_USER = "dbmasteruser"
DB_PASS = "$hP[W,r.<T^nM5.ta2Wc`V=Re{CQx=^*"
DB_HOST = "ls-ab0936cf312f45c43332fb5d5b0c869641a6646c.c9yuqw2e28nh.ap-northeast-2.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "postgres"

# URL encoding is required because the password contains special characters ($, [, ^, etc.)
safe_password = urllib.parse.quote_plus(DB_PASS)

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Engine Configuration
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
