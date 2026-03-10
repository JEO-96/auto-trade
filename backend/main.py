import logging
from contextlib import asynccontextmanager
from log_config import setup_logging
setup_logging(level=logging.INFO)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import models, database, bot_manager
from routers import auth, bots, keys, backtest, admin, community
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
