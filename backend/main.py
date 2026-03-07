from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models, database
from routers import auth, bots, keys, backtest

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Momentum Breakout Trading API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bots.router)
app.include_router(keys.router)
app.include_router(backtest.router)
