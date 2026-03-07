import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL Connection String Format: postgresql://username:password@localhost:5432/database_name
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost/postgres"

# For PostgreSQL, remove 'connect_args={"check_same_thread": False}' which is SQLite specific
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
