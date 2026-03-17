from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Kakao OAuth
    kakao_rest_api_key: str = ""
    kakao_redirect_uri: str = "http://localhost:3000/auth/kakao"

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    db_user: str = "dbmasteruser"
    db_pass: str
    db_host: str
    db_port: str = "5432"
    db_name: str = "postgres"

    # Fernet Encryption Key
    fernet_key: str = ""

    # Exchange (optional - users set their own via dashboard)
    exchange_api_key: str = ""
    exchange_api_secret: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://backtested.bot",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
