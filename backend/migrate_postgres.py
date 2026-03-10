import psycopg2
import urllib.parse

# Using connection info from database.py
DB_USER = "dbmasteruser"
DB_PASS = "$hP[W,r.<T^nM5.ta2Wc`V=Re{CQx=^*"
DB_HOST = "ls-ab0936cf312f45c43332fb5d5b0c869641a6646c.c9yuqw2e28nh.ap-northeast-2.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "postgres"

try:
    conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # 1. Add kakao_id column if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN kakao_id VARCHAR")
        cursor.execute("CREATE UNIQUE INDEX ix_users_kakao_id ON users (kakao_id)")
        print("Column kakao_id added.")
    except Exception as e:
        conn.rollback()
        print(f"kakao_id might already exist or error: {e}")
    else:
        conn.commit()

    # 2. Add created_at column if not exists
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("Column created_at added.")
    except Exception as e:
        conn.rollback()
        print(f"created_at might already exist or error: {e}")
    else:
        conn.commit()

    # 3. Make hashed_password nullable
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL")
        print("hashed_password set to nullable.")
    except Exception as e:
        conn.rollback()
        print(f"Error making hashed_password nullable: {e}")
    else:
        conn.commit()

    # 5. Add nickname column if not exists
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN nickname VARCHAR")
        print("Column nickname added.")
    except Exception as e:
        conn.rollback()
        print(f"nickname might already exist or error: {e}")
    else:
        conn.commit()

    # 6. Add kakao_access_token column if not exists
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN kakao_access_token VARCHAR")
        print("Column kakao_access_token added.")
    except Exception as e:
        conn.rollback()
        print(f"kakao_access_token might already exist or error: {e}")
    else:
        conn.commit()

    cursor.close()
    conn.close()
    print("PostgreSQL migration complete.")

except Exception as e:
    print(f"Critical connection error: {e}")
