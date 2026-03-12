import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from log_config import setup_logging

setup_logging(level=logging.INFO)

import bot_manager
import database
import models
from routers import admin, auth, backtest, bots, community, credits, keys
from routers import settings as settings_router
from settings import settings

models.Base.metadata.create_all(bind=database.engine)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 이전에 가동 중이던 봇 자동 복구
    await bot_manager.recover_active_bots()
    yield
    # Shutdown: 모든 봇 안전 종료 (포지션 DB 보존)
    await bot_manager.graceful_shutdown()


app = FastAPI(title="Momentum Breakout Trading API", lifespan=lifespan)

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
app.include_router(credits.router)
app.include_router(settings_router.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
