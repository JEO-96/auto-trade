# CLAUDE.md — AI Assistant Guide for auto-trade

## Project Overview

**auto-trade** is a full-stack cryptocurrency algorithmic trading platform with community features.
- **Backend:** FastAPI (Python 3.12) with PostgreSQL (AWS RDS)
- **Frontend:** Next.js 14 (TypeScript) with Tailwind CSS
- **Infrastructure:** Docker Compose, Nginx (SSL), GitHub Actions CI/CD
- **Exchange:** Upbit via CCXT library
- **Auth:** Kakao OAuth 2.0 + JWT (admin approval required for new users)
- **Production URL:** https://jooeunoh.com

---

## Repository Structure

```
auto-trade/
├── backend/                    # FastAPI Python application
│   ├── main.py                 # App entry point, CORS config, router registration, rate limiting
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── database.py             # PostgreSQL connection (AWS RDS) with connection pooling
│   ├── settings.py             # Pydantic BaseSettings — centralized config from .env
│   ├── auth.py                 # JWT creation/verification helpers (reads from settings)
│   ├── dependencies.py         # FastAPI Depends() providers (get_db, get_current_user, get_admin_user)
│   ├── bot_manager.py          # Async bot task lifecycle management
│   ├── notifications.py        # Kakao Talk message notifications
│   ├── crypto_utils.py         # Fernet encryption/decryption for API keys
│   ├── log_config.py           # Centralized logging setup
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile
│   ├── .env.example
│   ├── migrate_*.py            # Migration scripts (historical schema evolution)
│   ├── routers/
│   │   ├── auth.py             # POST /auth/token, POST /auth/kakao, POST /auth/kakao/complete, GET /auth/me
│   │   ├── backtest.py         # Backtest CRUD + share to community
│   │   ├── bots.py             # Bot CRUD + start/stop/status/logs
│   │   ├── keys.py             # Exchange key management + balance query
│   │   ├── admin.py            # Admin: user listing, approval, rejection
│   │   └── community.py        # Community: posts, comments, likes, chat, profiles, strategy reviews
│   └── core/
│       ├── config.py           # Legacy config (Kakao API key)
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
│   │   │   ├── terms/page.tsx       # Terms of service
│   │   │   ├── auth/
│   │   │   │   ├── kakao/page.tsx       # Kakao OAuth callback
│   │   │   │   └── register-email/page.tsx # Manual email registration (Kakao users without email)
│   │   │   ├── community/
│   │   │   │   ├── layout.tsx       # Public community layout
│   │   │   │   ├── page.tsx         # Public community post listing
│   │   │   │   └── post/page.tsx    # Public post detail view
│   │   │   └── dashboard/
│   │   │       ├── layout.tsx  # Sidebar navigation
│   │   │       ├── page.tsx    # Bot control + trade log viewer
│   │   │       ├── backtest/page.tsx
│   │   │       ├── keys/page.tsx
│   │   │       ├── admin/page.tsx       # Admin user management panel
│   │   │       ├── profile/page.tsx     # User profile page
│   │   │       └── community/
│   │   │           ├── page.tsx         # Community post listing
│   │   │           ├── post/page.tsx    # Single post detail view
│   │   │           ├── create/page.tsx  # Create new post
│   │   │           ├── profile/page.tsx # Community user profile
│   │   │           └── chat/page.tsx    # Real-time chat
│   │   ├── components/
│   │   │   ├── AuthGuard.tsx           # JWT-based route protection
│   │   │   ├── KakaoLoginButton.tsx
│   │   │   ├── RiskDisclaimerModal.tsx # Risk warning modal for live trading
│   │   │   └── ui/                     # StatCard, NavItem, Badge, Button, Input, LoadingSpinner, EmptyState, PageContainer
│   │   ├── types/
│   │   │   ├── index.ts        # Type re-exports
│   │   │   ├── user.ts         # User types
│   │   │   ├── bot.ts          # Bot config & trade log types
│   │   │   ├── keys.ts         # Exchange key types
│   │   │   ├── backtest.ts     # Backtest request/response types
│   │   │   └── community.ts    # Community post, comment, chat types
│   │   └── lib/
│   │       ├── api.ts          # Axios instance with auth interceptors
│   │       ├── api/            # Modular API functions
│   │       │   ├── index.ts    # Re-exports all API modules
│   │       │   ├── auth.ts     # Auth API calls
│   │       │   ├── bot.ts      # Bot CRUD & control API calls
│   │       │   ├── keys.ts     # Exchange key API calls
│   │       │   ├── backtest.ts # Backtest API calls
│   │       │   ├── admin.ts    # Admin API calls
│   │       │   └── community.ts # Community API calls
│   │       ├── constants.ts    # Symbols, strategies, timeframes, poll intervals
│   │       └── utils.ts        # Shared utility functions
│   ├── package.json
│   ├── tsconfig.json           # Path alias: @/* → src/*
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf              # SSL termination, /api/* → backend, /* → frontend
│   └── Dockerfile
├── docker-compose.yml          # Orchestrates: backend, frontend, nginx
├── .github/workflows/deploy.yml # SSH deploy to server on push to main
├── .claude/agents/             # Custom AI agent definitions (if present)
├── main.py, strategy.py, ...   # Legacy standalone scripts (not used by the app)
└── README.md                   # Korean-language project documentation
```

---

## Development Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # fill in all credentials (see below)
python main.py              # starts uvicorn on port 8000
```

Environment variables (see `backend/.env.example`):
- `KAKAO_REST_API_KEY` — Kakao REST API key
- `KAKAO_REDIRECT_URI` — Kakao OAuth redirect (default: `http://localhost:3000/auth/kakao`)
- `SECRET_KEY` — JWT signing key (generate with `openssl rand -hex 32`)
- `FERNET_KEY` — Fernet encryption key for API keys (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, `DB_NAME` — PostgreSQL credentials
- `EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET` — Optional Upbit keys (users set their own via dashboard)

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
**Connection:** defined in `backend/database.py` (connection pooling: pool_size=10, max_overflow=20)

### Models (`backend/models.py`)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `User` | id, email, nickname, kakao_id, kakao_access_token, kakao_refresh_token, is_active, is_admin, created_at | `is_active` defaults to `False` (admin approval required); `is_admin` gates admin features |
| `ExchangeKey` | user_id, exchange_name, api_key_encrypted, api_secret_encrypted | Encrypted with Fernet via `crypto_utils.py` |
| `BotConfig` | user_id, symbol, timeframe, strategy_name, is_active, paper_trading_mode, allocated_capital | Holds strategy params (rsi_period, macd_fast, macd_slow, volume_ma_period) |
| `TradeLog` | bot_id, symbol, side, price, amount, pnl, reason | side: BUY/SELL; reason: Entry/Stop Loss/Take Profit |
| `OHLCV` | symbol, timeframe, timestamp, open, high, low, close, volume | Caching layer to reduce CCXT API calls |
| `BacktestHistory` | user_id, symbols, timeframe, strategy_name, initial_capital, final_capital, total_trades, result_data, status | Persistent backtest results |
| `ActivePosition` | bot_id, symbol, position_amount, entry_price, stop_loss, take_profit | Bot position persistence for server restart recovery |
| `CommunityPost` | user_id, post_type, title, content, backtest_data, performance_data, strategy_name, rating, like_count, comment_count, is_deleted | Post types: backtest_share, performance_share, strategy_review, discussion |
| `PostComment` | post_id, user_id, content, is_deleted | Soft-delete comments |
| `PostLike` | post_id, user_id | Unique constraint per user per post |
| `ChatMessage` | user_id, content, created_at | Simple chat messages |

### Migrations

Migration scripts in `backend/`:
```bash
python migrate_db.py                # initial migration
python migrate_db_v2.py             # v2 schema changes
python migrate_postgres.py          # PostgreSQL migration
python migrate_active_positions.py  # active_positions table
python migrate_admin.py             # admin fields (is_admin, created_at)
python migrate_community.py         # community tables (posts, comments, likes)
python migrate_kakao_refresh.py     # kakao_refresh_token field
```

---

## API Routes

All routes except `/auth/*` and some `/community/*` GETs require `Authorization: Bearer <jwt>` header.

### Auth (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/token` | Email/password login → JWT (rate limited: 10/min) |
| POST | `/auth/kakao` | Kakao OAuth code → JWT (may return `requires_email` if email not provided) |
| POST | `/auth/kakao/complete` | Complete registration with manual email input |
| GET | `/auth/me` | Current user info |

### Bots (`/bot`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/bot/` | Create new bot config (max 5/user, live max 1/user) |
| PUT | `/bot/{bot_id}` | Update bot config (stopped state only) |
| DELETE | `/bot/{bot_id}` | Delete bot + related data (stopped state only) |
| POST | `/bot/start/{bot_id}` | Start async trading bot |
| POST | `/bot/stop/{bot_id}` | Stop bot (warns about live positions) |
| GET | `/bot/status/{bot_id}` | Running/Stopped status |
| GET | `/bot/logs/{bot_id}` | Trade log history (last 100) |
| GET | `/bot/list` | List current user's bots |

### Keys (`/keys`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/keys/` | Add/update exchange API key (Fernet encrypted) |
| GET | `/keys/` | List saved keys (preview only) |
| GET | `/keys/balance` | Fetch Upbit account balances via CCXT |

### Backtest (`/backtest`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/backtest/` | Run single-symbol backtest |
| POST | `/backtest/portfolio` | Run multi-symbol portfolio backtest |
| GET | `/backtest/status/{task_id}` | Poll backtest progress/results |
| GET | `/backtest/history` | List backtest history (paginated) |
| GET | `/backtest/history/{history_id}` | Get backtest history detail |
| DELETE | `/backtest/history/{history_id}` | Delete backtest history record |
| POST | `/backtest/history/{history_id}/share` | Share backtest result to community |

### Admin (`/admin`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/users` | List all users (admin only) |
| GET | `/admin/users/pending` | List pending approval users (admin only) |
| POST | `/admin/users/{user_id}/approve` | Approve user (set is_active=True) |
| POST | `/admin/users/{user_id}/reject` | Reject user (set is_active=False) |

### Community (`/community`)
| Method | Path | Description |
|--------|------|-------------|
| PUT | `/community/profile/nickname` | Update nickname (2-20 chars, unique) |
| GET | `/community/profile/{user_id}` | Get user profile |
| GET | `/community/posts` | List posts (paginated, filterable by post_type) |
| POST | `/community/posts` | Create post |
| GET | `/community/posts/{post_id}` | Get single post |
| PUT | `/community/posts/{post_id}` | Update own post |
| DELETE | `/community/posts/{post_id}` | Soft-delete post (own or admin) |
| POST | `/community/posts/{post_id}/like` | Toggle like |
| GET | `/community/posts/{post_id}/comments` | List comments |
| POST | `/community/posts/{post_id}/comments` | Create comment |
| DELETE | `/community/comments/{comment_id}` | Soft-delete comment (own or admin) |
| GET | `/community/chat` | Get chat messages (supports `after_id` polling) |
| POST | `/community/chat` | Send chat message (max 500 chars) |
| GET | `/community/strategies/{strategy_name}/reviews` | Get strategy reviews |
| GET | `/community/strategies/{strategy_name}/rating` | Get average strategy rating |

---

## Key Architectural Patterns

### 1. Centralized Configuration
`backend/settings.py` — `pydantic_settings.BaseSettings` loads all config from `.env` file.
All modules import from `settings.settings` instead of using hardcoded values.
DB credentials, JWT secret, Fernet key, CORS origins are all configurable via environment variables.

### 2. Strategy Factory Pattern
`backend/core/strategy.py` — `get_strategy(name: str)` returns a strategy instance.
Strategy names have aliases (e.g., `james_pro_stable` and `momentum_stable` both map to `MomentumBreakoutProStableStrategy`).
Add new strategies by creating a class in `backend/core/strategies/` and registering in the factory.

### 3. Async Bot Management & Position Persistence
`backend/bot_manager.py` — maintains a `Dict[int, asyncio.Task]` called `active_bots`.
Bot loops run as asyncio tasks; `start_bot()` / `stop_bot()` manage the lifecycle.

Key features:
- **Position persistence**: Positions saved to `ActivePosition` table every tick; loaded on bot restart
- **Graceful shutdown**: `graceful_shutdown()` cancels all tasks with timeout, preserving positions in DB
- **Auto-recovery**: `recover_active_bots()` restores bots marked `is_active=True` on server startup
- **Lifespan events**: `main.py` uses `asynccontextmanager` lifespan for startup recovery + shutdown
- **Bot limits**: Max 5 bots/user total, max 1 live (실매매) bot/user, unlimited paper (모의투자) bots

### 4. Rate Limiting
`backend/main.py` uses `slowapi` for rate limiting. Auth endpoints are limited to 10 requests/minute per IP.

### 5. Fernet Encryption for API Keys
`backend/crypto_utils.py` — provides `encrypt_key()` / `decrypt_key()` using Fernet symmetric encryption.
Requires `FERNET_KEY` environment variable. All exchange API key storage uses this module.

### 6. Backtest Task Registry with DB Persistence
`backend/routers/backtest.py` — backtest tasks run in threads, tracked in-memory by UUID.
Results are persisted to `BacktestHistory` table on completion for later retrieval.
Backtest results can be shared to community via `/backtest/history/{id}/share`.

### 7. Data Caching
`backend/core/data_fetcher.py` — checks `OHLCV` table before calling CCXT API.
Prevents rate limit issues; always prefer using `DataFetcher` over raw CCXT calls.

### 8. Paper Trading
`backend/core/execution.py` — `ExecutionEngine` wraps real and paper trading behind the same interface.
`BotConfig.paper_trading_mode = True` prevents real orders from being placed.

### 9. Admin Approval System
New users register with `is_active=False`. Admins (`is_admin=True`) approve users via `/admin/users/{id}/approve`.
Unapproved users cannot log in (403 Forbidden).

### 10. Dependency Injection
`backend/dependencies.py` — provides:
- `get_db()` — yields DB session
- `get_current_user()` — validates JWT, checks `is_active`
- `get_current_user_optional()` — returns `None` if no valid token (for public routes)
- `get_admin_user()` — validates JWT + checks `is_admin`

### 11. Frontend API Client
`frontend/src/lib/api.ts` — Axios instance that automatically attaches JWT from localStorage.
All API calls must go through this client, never fetch directly.

### 12. Frontend Constants
`frontend/src/lib/constants.ts` — centralized strategy lists, symbol lists, timeframes, and poll intervals.
Separate `STRATEGIES` (for backtest) and `BOT_STRATEGIES` (for bot creation) lists.

---

## Trading Strategies

All strategies are in `backend/core/strategies/` and follow a common interface.

| Strategy | Aliases | Profile | Volume Threshold | RR Ratio | Description |
|----------|---------|---------|-----------------|----------|-------------|
| `momentum_breakout_basic` | — | Baseline | — | 1:2 | Simple momentum breakout (fallback for unknown names) |
| `momentum_breakout_pro_stable` | `james_pro_stable`, `momentum_stable` | Conservative | 2.1x | 1:2 | Tight stops, lower drawdown |
| `momentum_breakout_pro_aggressive` | `james_pro_aggressive`, `momentum_aggressive` | Aggressive | 1.8x | 1:2 | Loose stops, higher upside |
| `momentum_breakout_elite` | `james_pro_elite`, `momentum_elite` | Elite | 1.3x | 1:5 | 3 entry signals (breakout/trend rider/pullback), hyper-growth |
| `steady_compounder` | — | Swing | ≥ avg | 1:3 | OR-based signals (RSI bounce/MACD cross/EMA bounce), 4h optimized |

Default strategy: `momentum_stable`

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

## Security Notes

> Previously known issues and their current status:

1. **~~Hardcoded DB credentials~~** — **FIXED.** `backend/database.py` now reads from `settings.py` (pydantic-settings from `.env`).
2. **~~Fake encryption~~** — **FIXED.** `backend/crypto_utils.py` uses Fernet symmetric encryption. String reversal replaced.
3. **~~Hardcoded JWT secret~~** — **FIXED.** `backend/auth.py` reads `SECRET_KEY` from `settings.py`.
4. **No test suite** — The project has no automated tests. Add tests before adding new critical features.
5. **Kakao tokens stored in DB** — `kakao_access_token` and `kakao_refresh_token` stored in plain text in `User` table. Consider encrypting.

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
- Use `Depends(get_admin_user)` for admin-only routes
- Use `Depends(get_current_user_optional)` for routes with optional auth
- All configuration via `settings.py` — never hardcode secrets
- All API key encryption via `crypto_utils.py` — never store keys in plain text
- Korean comments are acceptable (existing codebase uses Korean)
- Centralized logging via `log_config.py` — use `logging.getLogger(__name__)` in modules

### TypeScript (Frontend)
- Functional components with React hooks only — no class components
- All API calls via `frontend/src/lib/api.ts` (the Axios instance)
- Strategy/symbol/timeframe constants in `frontend/src/lib/constants.ts`
- Use `@/` path alias (resolves to `src/`)
- Tailwind CSS for all styling; custom classes defined in `globals.css`
- Auth state managed via localStorage JWT + `AuthGuard` component
- UI text may be Korean (existing codebase convention)
- Reusable UI components in `frontend/src/components/ui/`

### Git
- Main production branch: `main`
- Feature branches: `feature/<description>` or `claude/<description>`
- CI/CD deploys automatically from `main`

---

## Common Tasks

### Add a new trading strategy
1. Create `backend/core/strategies/my_strategy.py` implementing the strategy interface
2. Register it in `backend/core/strategy.py` `STRATEGY_MAP` dict
3. Add the strategy name in `frontend/src/lib/constants.ts` (both `STRATEGIES` and `BOT_STRATEGIES` arrays)

### Add a new API endpoint
1. Add route handler in the appropriate `backend/routers/*.py` file
2. Add Pydantic schema to `backend/schemas.py` if needed
3. Register the router in `backend/main.py` if it's a new router file
4. Update `frontend/src/lib/api.ts` with the new API call function

### Add a new database model
1. Define the SQLAlchemy model in `backend/models.py`
2. Create a migration script `backend/migrate_<description>.py`
3. Add corresponding Pydantic schemas in `backend/schemas.py`

### Add admin-only functionality
1. Use `Depends(get_admin_user)` from `dependencies.py` in route handlers
2. Add frontend page under `frontend/src/app/dashboard/admin/`

### Run a backtest manually
```bash
# Via API (after auth):
curl -X POST https://jooeunoh.com/api/backtest/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/KRW", "timeframe": "4h", "strategy_name": "james_pro_elite"}'
```

---

## Dependencies Quick Reference

### Backend Key Packages
| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `sqlalchemy` | ORM |
| `pydantic-settings` | Config management from .env |
| `ccxt` | Exchange API (Upbit, etc.) |
| `pandas`, `numpy` | Data manipulation |
| `pandas-ta` | Technical indicators (RSI, MACD) |
| `vectorbt` | Vectorized backtesting |
| `python-jose` | JWT |
| `bcrypt` | Password hashing |
| `httpx` | Async HTTP client |
| `cryptography` | Fernet encryption for API keys |
| `slowapi` | Rate limiting |

### Frontend Key Packages
| Package | Purpose |
|---------|---------|
| `next` | React framework (App Router) |
| `axios` | HTTP client |
| `lucide-react` | Icon library |
| `tailwindcss` | CSS utility framework |
