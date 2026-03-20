import sqlite3
import os

db_path = "trading_bot.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Add kakao_id column
        cursor.execute("ALTER TABLE users ADD COLUMN kakao_id VARCHAR")
        print("Column kakao_id added to users table.")
        
        # 2. Make hashed_password nullable (SQLite doesn't easily allow this without recreating table)
        # But we can just leave it as is if it was already NOT NULL.
        # However, for new users it needs to be nullable.
        # Let's check current schema.
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("Current users table schema:", columns)
        
    except sqlite3.OperationalError as e:
        if "duplicate column name: kakao_id" in str(e):
            print("Column kakao_id already exists.")
        else:
            print(f"Error: {e}")
    
    conn.commit()
    conn.close()
else:
    print("Database file not found. It will be created on next app run with correct schema.")
