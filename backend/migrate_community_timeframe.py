"""
Migration script to add 'timeframe' column to community_posts table.
Used for strategy review posts to store the candle period (e.g., 1h, 4h, 1d).

Usage:
    cd backend
    python migrate_community_timeframe.py
"""

from database import engine

if __name__ == "__main__":
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_columns = [col["name"] for col in inspector.get_columns("community_posts")]

    if "timeframe" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE community_posts ADD COLUMN timeframe VARCHAR NULL"))
        print("Added 'timeframe' column to community_posts table.")
    else:
        print("Column 'timeframe' already exists in community_posts table.")

    print("Migration complete.")
