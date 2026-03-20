"""
Migration script for community feature tables.
Creates: community_posts, post_comments, post_likes, chat_messages

Usage:
    cd backend
    python migrate_community.py
"""

from database import engine, Base
import models  # noqa: F401 - ensures all models are registered with Base

if __name__ == "__main__":
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing = inspector.get_table_names()
    tables = ["community_posts", "post_comments", "post_likes", "chat_messages", "backtest_history"]

    for t in tables:
        if t not in existing:
            models.Base.metadata.tables[t].create(bind=engine)
            print(f"Created table: {t}")
        else:
            print(f"Table already exists: {t}")

    print("Community migration complete.")
