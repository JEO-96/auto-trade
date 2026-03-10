# CLAUDE.md — AI Assistant Guide for auto-trade

## Project Overview

**auto-trade** is a full-stack cryptocurrency algorithmic trading platform.
- **Backend:** FastAPI (Python 3.12) with PostgreSQL (AWS RDS)
- **Frontend:** Next.js 14 (TypeScript) with Tailwind CSS
- **Infrastructure:** Docker Compose, Nginx (SSL), GitHub Actions CI/CD
- **Exchange:** Upbit via CCXT library
- **Auth:** Kakao OAuth 2.0 + JWT
- **Production URL:** https://jooeunoh.com

---

## Repository Structure

```
auto-trade/
├── backend/                    # FastAPI Python application
│   ├── main.py                 # App entry point, CORS config, router registration
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── database.py             # PostgreSQL connection (AWS RDS)
│   ├── auth.py                 # JWT creation/verification helpers
│   ├── dependencies.py         # FastAPI Depends() providers
│   ├── bot_manager.py          # Async bot task lifecycle management
│   ├── notifications.py        # Kakao Talk message notifications
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile
│   ├── .env.example
│   ├── routers/
│   │   ├── auth.py             # POST /auth/token, POST /auth/kakao, GET /auth/me
│   │   ├── backtest.py         # POST /backtest/, POST /backtest/portfolio, GET /backtest/status/{id}
│   │   ├── bots.py             # POST /bot/start|stop/{id}, GET /bot/status|logs/{id}
│   │   └── keys.py             # POST /keys/, GET /keys/
│   └── core/
│       ├── data_fetcher.py     # CCXT OHLCV fetcher with PostgreSQL caching
│       ├── execution.py        # Paper/live trade execution engine
│       ├── strategy.py         # Strategy factory: get_strategy(name)
│       ├── vector_backtester.py # Vectorized backtesting with vectorbt
│       └── strategies/
│           ├── base.py                            # BaseStrategy: common indicators, trailing stop logic
│           ├── momentum_breakout_basic.py
│           ├── momentum_breakout_pro_stable.py   # Conservative: tight stops, 2.1x volume threshold
│           ├── momentum_breakout_pro_aggressive.py # Aggressive: loose stops, 1.8x volume threshold
│           ├── momentum_breakout_elite.py         # Hyper-growth: 3 entry signals, 1:5 RR
│           └── steady_compounder.py               # High win-rate swing: OR-based signals, 1:3 RR
├── frontend/                   # Next.js 14 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Landing page
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   ├── auth/kakao/page.tsx  # Kakao OAuth callback
│   │   │   └── dashboard/
│   │   │       ├── layout.tsx  # Sidebar navigation
│   │   │       ├── page.tsx    # Bot control + trade log viewer
│   │   │       ├── backtest/page.tsx
│   │   │       └── keys/page.tsx
│   │   ├── components/
│   │   │   ├── AuthGuard.tsx   # JWT-based route protection
│   │   │   ├── KakaoLoginButton.tsx
│   │   │   └── ui/             # StatCard, NavItem
│   │   └── lib/
│   │       └── api.ts          # Axios instance with auth interceptors
│   ├── package.json
│   ├── tsconfig.json           # Path alias: @/* → src/*
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf              # SSL termination, /api/* → backend, /* → frontend
│   └── Dockerfile
├── docker-compose.yml          # Orchestrates: backend, frontend, nginx
├── .github/workflows/deploy.yml # SSH deploy to server on push to main
└── README.md                   # Korean-language project documentation
```

---

## Development Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # fill in Kakao OAuth credentials
python main.py              # starts uvicorn on port 8000
```

Environment variables needed (see `backend/.env.example`):
- `KAKAO_CLIENT_ID`
- `KAKAO_REDIRECT_URI`
- Database credentials (currently hardcoded in `database.py` — see security notes)

### Frontend

```bash
cd frontend
npm install
npm run dev                 # dev server on port 3000
npm run build               # production build
npm run lint                # ESLint
```

Set `NEXT_PUBLIC_API_URL` at build time (Docker build arg) for the API base URL.

### Full Stack (Docker Compose)

Production uses pre-built GHCR images (no local build needed):
```bash
docker-compose pull             # pull latest images from GHCR
docker-compose up -d            # start all services
docker-compose logs -f backend  # tail backend logs
docker-compose down             # stop all services
```

Services:
- `backend`: FastAPI on port 8000 (internal)
- `frontend`: Next.js on port 3000 (internal)
- `nginx`: Reverse proxy on ports 80/443 (public)

---

## Database

**Engine:** PostgreSQL (AWS RDS)
**ORM:** SQLAlchemy with declarative base
**Connection:** defined in `backend/database.py`

### Models (`backend/models.py`)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `User` | id, email, nickname, kakao_id, is_active | `is_active` gates access |
| `ExchangeKey` | user_id, exchange_name, api_key_encrypted, api_secret_encrypted | "Encryption" is currently string reversal — needs real encryption |
| `BotConfig` | user_id, symbol, timeframe, is_active, paper_trading_mode, allocated_capital | Holds strategy params |
| `TradeLog` | bot_id, symbol, side, price, amount, pnl, reason | side: BUY/SELL; reason: Entry/Stop Loss/Take Profit |
| `OHLCV` | symbol, timeframe, timestamp, open, high, low, close, volume | Caching layer to reduce CCXT API calls |
| `ActivePosition` | bot_id, symbol, position_amount, entry_price, stop_loss, take_profit | Bot position persistence for server restart recovery |

### Migrations

Run migration scripts directly when changing schema:
```bash
cd backend
python migrate_active_positions.py  # latest migration (active_positions table)
python migrate_postgres.py          # previous migration
```

Multiple migration files (`migrate_db.py`, `migrate_db_v2.py`, `migrate_postgres.py`, `migrate_active_positions.py`) exist for historical schema evolution.

---

## API Routes

All routes except `/auth/*` require `Authorization: Bearer <jwt>` header.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/token` | Email/password login → JWT |
| POST | `/auth/kakao` | Kakao OAuth code → JWT |
| GET | `/auth/me` | Current user info |
| POST | `/bot/` | Create new bot config (max 5/user, live max 1/user) |
| PUT | `/bot/{bot_id}` | Update bot config (stopped state only) |
| DELETE | `/bot/{bot_id}` | Delete bot + related data (stopped state only) |
| POST | `/bot/start/{bot_id}` | Start async trading bot |
| POST | `/bot/stop/{bot_id}` | Stop bot (awaits cancellation, clears positions) |
| GET | `/bot/status/{bot_id}` | Running/Stopped status |
| GET | `/bot/logs/{bot_id}` | Trade log history (last 100) |
| GET | `/bot/list` | List current user's bots |
| POST | `/keys/` | Add/update exchange API key |
| GET | `/keys/` | List saved keys (preview only) |
| POST | `/backtest/` | Run single-symbol backtest |
| POST | `/backtest/portfolio` | Run multi-symbol portfolio backtest |
| GET | `/backtest/status/{task_id}` | Poll backtest progress/results |
| DELETE | `/backtest/history/{history_id}` | Delete backtest history record |

---

## Key Architectural Patterns

### 1. Strategy Factory Pattern
`backend/core/strategy.py` — `get_strategy(name: str)` returns a strategy instance.
Add new strategies by creating a class in `backend/core/strategies/` and registering in the factory.

### 2. Async Bot Management & Position Persistence
`backend/bot_manager.py` — maintains a `Dict[int, asyncio.Task]` called `active_bots`.
Bot loops run as asyncio tasks; `start_bot()` / `stop_bot()` manage the lifecycle.

Key features:
- **Position persistence**: Positions saved to `ActivePosition` table every tick; loaded on bot restart
- **Graceful shutdown**: `graceful_shutdown()` cancels all tasks with timeout, preserving positions in DB
- **Auto-recovery**: `recover_active_bots()` restores bots marked `is_active=True` on server startup
- **Lifespan events**: `main.py` uses `asynccontextmanager` lifespan for startup recovery + shutdown
- **Bot limits**: Max 5 bots/user total, max 1 live (실매매) bot/user, unlimited paper (모의투자) bots

### 3. Backtest Task Registry
`backend/routers/backtest.py` — `backtest_tasks: Dict[str, dict]` stores progress by UUID.
Frontend polls `GET /backtest/status/{task_id}` for results. Tasks run in threads.

### 4. Data Caching
`backend/core/data_fetcher.py` — checks `OHLCV` table before calling CCXT API.
Prevents rate limit issues; always prefer using `DataFetcher` over raw CCXT calls.

### 5. Paper Trading
`backend/core/execution.py` — `ExecutionEngine` wraps real and paper trading behind the same interface.
`BotConfig.paper_trading_mode = True` prevents real orders from being placed.

### 6. Dependency Injection
`backend/dependencies.py` — provides `get_db()` (yields DB session) and `get_current_user()` (validates JWT).
Always use `Depends(get_db)` and `Depends(get_current_user)` in route handlers.

### 7. Frontend API Client
`frontend/src/lib/api.ts` — Axios instance that automatically attaches JWT from localStorage.
All API calls must go through this client, never fetch directly.

---

## Trading Strategies

All strategies are in `backend/core/strategies/` and follow a common interface.

| Strategy | Profile | Volume Threshold | RR Ratio | Description |
|----------|---------|-----------------|----------|-------------|
| `momentum_breakout_basic` | Baseline | — | 1:2 | Simple momentum breakout |
| `momentum_breakout_pro_stable` | Conservative | 2.1x | 1:2 | Tight stops, lower drawdown |
| `momentum_breakout_pro_aggressive` | Aggressive | 1.8x | 1:2 | Loose stops, higher upside |
| `momentum_breakout_elite` | Elite | 1.3x | 1:5 | 3 entry signals (breakout/trend rider/pullback), hyper-growth |
| `steady_compounder` | Swing | ≥ avg | 1:3 | OR-based signals (RSI bounce/MACD cross/EMA bounce), 4h optimized |

Signals use: RSI, MACD, Volume MA, EMA (20/50/100/200), ADX (via `pandas-ta`).
Parameters (`rsi_period`, `macd_fast`, `macd_slow`, `volume_ma_period`) are stored in `BotConfig`.

### Strategy Selection Guide
| Goal | Recommended Strategy | Timeframe |
|------|---------------------|-----------|
| 안정적 스윙 수익 | `steady_compounder` | 4h |
| 보수적 모멘텀 | `momentum_breakout_pro_stable` | 1h~4h |
| 공격적 모멘텀 | `momentum_breakout_pro_aggressive` | 1h~4h |
| 최대 수익 추구 | `momentum_breakout_elite` | 4h~1d |

### Important Notes
- **전략 로직 수정 금지**: 기존 전략의 신호 로직은 검증 완료됨. 파라미터/인프라 변경만 허용.
- **bot_manager.py limit=300**: Pro/Elite 전략은 `current_idx >= 200` 필요. limit이 작으면 신호 미발생.
- **새 전략 추가 시**: `backend/core/strategies/`에 클래스 생성 → `strategy.py` STRATEGY_MAP 등록 → `frontend/src/lib/constants.ts` 추가

---

## CI/CD

**Workflow:** `.github/workflows/deploy.yml` (2-job GHCR pipeline)
- **Build job** (GitHub Actions, ubuntu-latest, 7GB RAM): Builds 3 Docker images → pushes to GHCR (`ghcr.io/jeo-96/auto-trade/*`)
- **Deploy job**: SSHs into server → `docker-compose pull` → `docker-compose up -d`
- Triggers on push to `main` branch

**Why CI builds?** Production server has only 414MB RAM; Next.js build requires 1GB+. All builds happen on GitHub Actions.

**Docker images** (GHCR):
- `ghcr.io/jeo-96/auto-trade/backend:latest`
- `ghcr.io/jeo-96/auto-trade/frontend:latest`
- `ghcr.io/jeo-96/auto-trade/nginx:latest`

**Required GitHub Secrets:**
- `SERVER_IP`, `SERVER_USERNAME`, `SSH_PRIVATE_KEY` — SSH access
- `GHCR_PAT` — GitHub PAT with `read:packages`, `write:packages` for server-side GHCR pull

**To deploy:** merge/push to `main`. The deployment is fully automated.

---

## Security Issues to Be Aware Of

> These are known issues in the codebase. Do not make them worse; fix them when working nearby.

1. **Hardcoded DB credentials** — `backend/database.py` contains AWS RDS password in plain text. Should use `os.getenv()`.
2. **Fake encryption** — `backend/routers/keys.py` uses string reversal (`text[::-1]`) as "encryption". Should use `cryptography` (Fernet) or similar.
3. **Hardcoded JWT secret** — `backend/auth.py` has a hardcoded `SECRET_KEY`. Must move to environment variable.
4. **No test suite** — The project has no automated tests. Add tests before adding new critical features.

---

## Custom Agents (`.claude/agents/`)

프로젝트 전문 에이전트가 `.claude/agents/` 디렉토리에 정의되어 있습니다. 사용자가 특정 에이전트를 언급하거나 해당 도메인 작업을 요청할 때, 에이전트의 `instructions`을 참고하여 해당 관점으로 응답하세요.

| Agent | File | Role | When to Activate |
|-------|------|------|-----------------|
| **Senior Architect** | `architect.json` | 아키텍처, 클린코드, 코드리뷰 | 구조 설계, 리팩토링, 코드리뷰 요청 시 |
| **UI/UX Designer** | `designer.json` | 데이터 시각화, 대시보드 UX | UI 개선, 차트/대시보드 작업 시 |
| **Legal Compliance** | `legal.json` | 금융법, 가상자산법 준수 검토 | 전략 로직 변경, 법적 리스크 검토 시 |
| **Security Expert** | `security.json` | API키 유출, 보안 취약점 분석 | 보안 점검, 인증/암호화 작업 시 |
| **Trading Strategist** | `trader.json` | 퀀트 전략, 백테스팅 검증 | 전략 추가/수정, 백테스트 로직 검토 시 |

### Agent 사용 규칙
- 사용자가 "security 에이전트", "보안 점검해줘" 등으로 요청하면 해당 에이전트의 instructions를 로드하여 그 관점으로 분석
- 여러 에이전트를 조합할 수 있음 (예: architect + security로 코드리뷰)
- 에이전트 파일 경로: `.claude/agents/<name>.json`
- JSON 형식: `{ "name", "description", "instructions" }`

---

## Code Conventions

### Python (Backend)
- Use type hints on all function signatures
- Use `async def` for all route handlers
- Pydantic schemas in `schemas.py` for request/response validation
- SQLAlchemy models in `models.py`; never write raw SQL
- Use `Depends(get_db)` / `Depends(get_current_user)` in every protected route
- Korean comments are acceptable (existing codebase uses Korean)

### TypeScript (Frontend)
- Functional components with React hooks only — no class components
- All API calls via `frontend/src/lib/api.ts` (the Axios instance)
- Use `@/` path alias (resolves to `src/`)
- Tailwind CSS for all styling; custom classes defined in `globals.css`
- Auth state managed via localStorage JWT + `AuthGuard` component
- UI text may be Korean (existing codebase convention)

### Git
- Main production branch: `main`
- Feature branches: `feature/<description>` or `claude/<description>`
- CI/CD deploys automatically from `main`

---

## Common Tasks

### Add a new trading strategy
1. Create `backend/core/strategies/my_strategy.py` implementing the strategy interface
2. Register it in `backend/core/strategy.py` inside `get_strategy()`
3. Add the strategy name as an option in `frontend/src/app/dashboard/backtest/page.tsx`

### Add a new API endpoint
1. Add route handler in the appropriate `backend/routers/*.py` file
2. Add Pydantic schema to `backend/schemas.py` if needed
3. Register the router in `backend/main.py` if it's a new router file
4. Update `frontend/src/lib/api.ts` with the new API call function

### Add a new database model
1. Define the SQLAlchemy model in `backend/models.py`
2. Create a migration script `backend/migrate_<description>.py`
3. Add corresponding Pydantic schemas in `backend/schemas.py`

### Run a backtest manually
```bash
# Via API (after auth):
curl -X POST https://jooeunoh.com/api/backtest/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/KRW", "timeframe": "4h", "strategy": "momentum_breakout_pro_stable"}'
```

---

## Dependencies Quick Reference

### Backend Key Packages
| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `sqlalchemy` | ORM |
| `ccxt` | Exchange API (Upbit, etc.) |
| `pandas`, `numpy` | Data manipulation |
| `pandas-ta` | Technical indicators (RSI, MACD) |
| `vectorbt` | Vectorized backtesting |
| `python-jose` | JWT |
| `bcrypt` | Password hashing |
| `httpx` | Async HTTP client |

### Frontend Key Packages
| Package | Purpose |
|---------|---------|
| `next` | React framework (App Router) |
| `axios` | HTTP client |
| `lucide-react` | Icon library |
| `tailwindcss` | CSS utility framework |
