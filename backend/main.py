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

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 업비트 봇 자동 복구
    await bot_manager.recover_active_bots()

    # Startup: OKX 선물 봇 (API 키 설정된 경우만)
    okx_bot = None
    okx_task = None
    from settings import settings as app_settings
    if app_settings.okx_api_key and app_settings.okx_passphrase:
        try:
            okx_bot = OKXFuturesBot()
            okx_bot.initialize()
            okx_task = asyncio.create_task(okx_bot.run_loop())
            logger.info("OKX 선물 봇 시작됨 (업비트 봇과 동시 운영)")
        except Exception as e:
            logger.error(f"OKX 선물 봇 시작 실패: {e}")
    else:
        logger.info("OKX API 키 미설정 — OKX 봇 비활성")

    yield

    # Shutdown: OKX 봇 종료
    if okx_bot:
        okx_bot.stop()
        if okx_task:
            okx_task.cancel()
            try:
                await okx_task
            except asyncio.CancelledError:
                pass
        logger.info("OKX 선물 봇 종료됨")

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

logger = logging.getLogger(__name__)


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
