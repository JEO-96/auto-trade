"""마이그레이션: user_strategies 테이블 생성 + bot_configs/backtest_history 컬럼 추가"""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE backtest_history ADD COLUMN IF NOT EXISTS custom_params TEXT'))
    conn.execute(text('ALTER TABLE bot_configs ADD COLUMN IF NOT EXISTS custom_strategy_id INTEGER'))
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS user_strategies (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name VARCHAR NOT NULL,
            base_strategy_name VARCHAR NOT NULL,
            custom_params TEXT NOT NULL,
            backtest_history_id INTEGER REFERENCES backtest_history(id),
            created_at TIMESTAMP DEFAULT NOW(),
            is_deleted BOOLEAN DEFAULT FALSE,
            UNIQUE(user_id, name)
        )
    '''))
    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_user_strategies_user_id ON user_strategies(user_id)'))
    conn.commit()
    print('Migration complete')
