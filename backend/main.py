import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from log_config import setup_logging, setup_error_monitoring

setup_logging(level=logging.INFO)
setup_error_monitoring()

import bot_manager
import database
import models
from okx_futures.bot import OKXFuturesBot
from routers import admin, auth, backtest, bots, community, keys, strategies
from routers import settings as settings_router
from settings import settings

models.Base.metadata.create_all(bind=database.engine)

logger = logging.getLogger(__name__)


def _load_okx_credentials() -> dict | None:
    """OKX API 키를 DB(관리자) 또는 .env에서 로드. 없으면 None."""
    from crypto_utils import decrypt_key

    # 1) DB에서 관리자의 OKX 키 조회
    try:
        with database.get_db_session() as db:
            okx_key = db.query(models.ExchangeKey).filter(
                models.ExchangeKey.exchange_name == "okx"
            ).first()
            if okx_key:
                passphrase_enc = getattr(okx_key, "passphrase_encrypted", None)
                if passphrase_enc:
                    return {
                        "api_key": decrypt_key(okx_key.api_key_encrypted),
                        "secret_key": decrypt_key(okx_key.api_secret_encrypted),
                        "passphrase": decrypt_key(passphrase_enc),
                    }
    except Exception as e:
        logger.warning(f"OKX DB 키 조회 실패 (컬럼 미존재 가능): {e}")

    # 2) .env fallback
    from settings import settings as app_settings
    if app_settings.okx_api_key and app_settings.okx_passphrase:
        return {
            "api_key": app_settings.okx_api_key,
            "secret_key": app_settings.okx_secret_key,
            "passphrase": app_settings.okx_passphrase,
        }

    return None

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 업비트 봇 자동 복구
    await bot_manager.recover_active_bots()

    # OKX 선물 봇 — 자동시작 비활성화
    # 수동 활성화 필요 시 이 블록 주석 해제
    # okx_creds = _load_okx_credentials()
    # if okx_creds:
    #     okx_bot = OKXFuturesBot(credentials=okx_creds)
    #     okx_bot.initialize()
    #     okx_task = asyncio.create_task(okx_bot.run_loop())

    yield

    # Shutdown: 업비트 봇 안전 종료
    await bot_manager.graceful_shutdown()


app = FastAPI(title="Backtested Trading API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bots.router)
app.include_router(keys.router)
app.include_router(backtest.router)
app.include_router(admin.router)
app.include_router(community.router)
app.include_router(strategies.router)
app.include_router(settings_router.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외를 로깅하고 500 응답 반환."""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
