import sqlite3
import os

db_path = "trading_bot.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Add created_at column
        cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
        print("Column created_at added to users table.")
    except sqlite3.OperationalError:
        print("Column created_at already exists.")

    try:
        # 2. Set default is_active to 0 for users if needed
        # (Actually the SQLAlchemy model will handle new users, 
        # but existing users might stay as 1)
        pass
        
    except Exception as e:
        print(f"Error: {e}")
    
    conn.commit()
    conn.close()
    print("Migration finished.")
else:
    print("Database file not found.")
