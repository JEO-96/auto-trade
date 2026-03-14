# CLAUDE.md — AI Assistant Guide for Backtested

## Project Overview

**Backtested** (backtested.bot) is a full-stack algorithmic trading platform with community features and a performance-based credit system.
- **Backend:** FastAPI (Python 3.12) with PostgreSQL (AWS RDS)
- **Frontend:** Next.js 14 (TypeScript) with Tailwind CSS
- **Infrastructure:** Docker Compose, Nginx (SSL), GitHub Actions CI/CD
- **Exchange:** Upbit/Bithumb via CCXT library (주식 확장 예정)
- **Auth:** Kakao OAuth 2.0 + JWT (가입 즉시 로그인 가능, 관리자 승인 불필요)
- **Credit System:** 성과 기반 수수료 (수익 10% 차감, 손실 10% 환불), 토스페이먼츠 결제 연동
- **Production URL:** https://backtested.bot

---

## Repository Structure

```
backtested/
├── backend/                    # FastAPI Python application
│   ├── main.py                 # App entry point, CORS config, router registration, rate limiting
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── database.py             # PostgreSQL connection (AWS RDS) with connection pooling
│   ├── settings.py             # Pydantic BaseSettings — centralized config from .env
│   ├── auth.py                 # JWT creation/verification helpers (reads from settings)
│   ├── dependencies.py         # FastAPI Depends() providers (get_db, get_current_user, get_admin_user, get_user_or_404)
│   ├── bot_manager.py          # Async bot task lifecycle management
│   ├── credit_service.py       # Credit balance management & trade fee processing
│   ├── notifications.py        # Telegram bot notifications (카테고리별: trade, bot_status, system)
│   ├── error_monitor.py        # TelegramErrorHandler — ERROR 이상 로그를 텔레그램으로 관리자 전송
│   ├── crypto_utils.py         # Fernet encryption/decryption + API key masking + create_exchange() factory + encrypt_token/decrypt_token
│   ├── kakao_service.py        # Kakao OAuth token exchange & user info (decoupled from router)
│   ├── utils.py                # Common helpers (safe_json_loads, parse_symbols, mask_nickname)
│   ├── log_config.py           # Centralized logging setup
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile
│   ├── .env.example
│   ├── migrate_*.py            # Migration scripts (historical schema evolution)
│   ├── tests/
│   │   ├── conftest.py         # Test fixtures (DB session, mock users)
│   │   └── test_core_logic.py  # 핵심 로직 단위 테스트 (크레딧, 봇, 포지션)
│   ├── scripts/
│   │   └── check_rds_backup.py # AWS RDS 백업 정책 검증 스크립트
│   ├── routers/
│   │   ├── auth.py             # POST /auth/token, POST /auth/kakao, POST /auth/kakao/complete, GET /auth/me, GET/PUT /auth/notifications
│   │   ├── backtest.py         # Backtest CRUD + share to community
│   │   ├── bots.py             # Bot CRUD + start/stop/status/logs/performance + credit check + active bots
│   │   ├── credits.py          # Credit balance, history, Toss Payments integration
│   │   ├── keys.py             # Exchange key management + balance query
│   │   ├── admin.py            # Admin: dashboard stats, user listing, approval, rejection, credit adjustment
│   │   └── community.py        # Community: posts, comments, likes, chat, profiles, strategy reviews, leaderboard, strategy-rankings, telegram
│   └── core/
│       ├── config.py           # Trading parameters (RISK_PER_TRADE, RSI/MACD defaults)
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
│   │   │   ├── privacy/page.tsx    # Privacy policy (개인정보처리방침)
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
│   │   │       ├── performance/page.tsx   # 봇 성과 분석 (수익률 차트, PnL, 드로다운)
│   │   │       ├── live-bots/page.tsx     # 실시간 봇 현황 (공개)
│   │   │       ├── settings/page.tsx      # 시스템 설정
│   │   │       ├── admin/page.tsx         # Admin user management panel
│   │   │       ├── profile/page.tsx       # User profile page
│   │   │       ├── community/
│   │   │       │   ├── page.tsx           # Community post listing
│   │   │       │   ├── post/page.tsx      # Single post detail view
│   │   │       │   ├── create/page.tsx    # Create new post
│   │   │       │   ├── profile/page.tsx   # Community user profile
│   │   │       │   ├── chat/page.tsx      # Real-time chat
│   │   │       │   └── leaderboard/page.tsx # 수익률 리더보드 + 전략 랭킹
│   │   │       └── credits/
│   │   │           └── page.tsx           # Credit balance, history, Toss payment
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx          # Auth state context (useAuth hook)
│   │   ├── components/
│   │   │   ├── AuthGuard.tsx           # JWT-based route protection
│   │   │   ├── KakaoLoginButton.tsx
│   │   │   ├── RiskDisclaimerModal.tsx # Risk warning modal for live trading
│   │   │   ├── OnboardingGuide.tsx     # 첫 방문 시 단계별 온보딩 안내
│   │   │   ├── ServiceWorkerRegistration.tsx # PWA 서비스 워커 등록
│   │   │   └── ui/                     # StatCard, NavItem, Badge, Button, Input, LoadingSpinner, EmptyState, PageContainer, Toast
│   │   ├── modals/
│   │   │   ├── DeleteConfirmationModal.tsx  # Reusable delete confirmation dialog
│   │   │   ├── ConfirmationModal.tsx        # General-purpose confirmation dialog
│   │   │   └── BotFormModal.tsx             # Bot create/edit form modal
│   │   ├── cards/
│   │   │   └── BotCard.tsx                  # Bot status card with live/paper visual distinction
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
│   │       │   ├── credits.ts  # Credit & payment API calls
│   │       │   └── community.ts # Community API calls
│   │       ├── constants.ts    # Symbols, strategies, timeframes, poll intervals
│   │       └── utils.ts        # Shared utility functions
│   ├── public/
│   │   ├── manifest.json       # PWA manifest
│   │   ├── sw.js               # Service worker (오프라인 캐시)
│   │   └── icons/              # PWA icons (192/512, maskable, apple-touch)
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
- `TELEGRAM_BOT_TOKEN` — Telegram bot token for notifications
- `TELEGRAM_CHAT_ID` — Default Telegram chat ID
- `TOSS_CLIENT_KEY` — Toss Payments client key (`test_ck_...` for dev, `live_ck_...` for prod)
- `TOSS_SECRET_KEY` — Toss Payments secret key (`test_sk_...` for dev, `live_sk_...` for prod)

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
| `User` | id, email, nickname, kakao_id, kakao_access_token, kakao_refresh_token, telegram_chat_id, notification_trade, notification_bot_status, notification_system, is_active, is_admin, created_at | `is_active` defaults to `True` (auto-approved); `is_admin` gates admin features; `notification_*` boolean fields for per-category alert control |
| `ExchangeKey` | user_id, exchange_name, api_key_encrypted, api_secret_encrypted | Encrypted with Fernet via `crypto_utils.py` |
| `BotConfig` | user_id, symbol, timeframe, exchange_name, strategy_name, is_active, paper_trading_mode, allocated_capital | `exchange_name` selects exchange (upbit/bithumb); Holds strategy params (rsi_period, macd_fast, macd_slow, volume_ma_period) |
| `TradeLog` | bot_id, symbol, side, price, amount, pnl, reason | side: BUY/SELL; reason: Entry/Stop Loss/Take Profit |
| `OHLCV` | symbol, timeframe, timestamp, open, high, low, close, volume | Caching layer to reduce CCXT API calls |
| `BacktestHistory` | user_id, symbols, timeframe, strategy_name, initial_capital, final_capital, total_trades, result_data, status | Persistent backtest results |
| `ActivePosition` | bot_id, symbol, position_amount, entry_price, stop_loss, take_profit | Bot position persistence for server restart recovery |
| `CommunityPost` | user_id, post_type, title, content, backtest_data, performance_data, strategy_name, rating, like_count, comment_count, is_deleted | Post types: backtest_share, performance_share, strategy_review, discussion |
| `PostComment` | post_id, user_id, content, is_deleted | Soft-delete comments |
| `PostLike` | post_id, user_id | Unique constraint per user per post |
| `UserCredit` | user_id, balance, total_earned, total_spent | 크레딧 잔액 (가입 시 1000 지급) |
| `CreditTransaction` | user_id, amount, balance_after, tx_type, reference_id, description | 크레딧 변동 이력 (signup_bonus, profit_fee, loss_refund, purchase, admin_adjust) |
| `PaymentOrder` | user_id, order_id, amount, credits, status, payment_key, method | 토스페이먼츠 결제 주문 (pending → confirmed/failed) |
| `ChatMessage` | user_id, content, created_at | Simple chat messages |
| `SystemSettings` | key, value | Key-value system configuration (JSON string values) |

### Migrations

Migration scripts in `backend/`:
```bash
python migrate_db.py                # initial migration
python migrate_db_v2.py             # v2 schema changes
python migrate_postgres.py          # PostgreSQL migration
python migrate_active_positions.py  # active_positions table
python migrate_admin.py             # admin fields (is_admin, created_at)
python migrate_community.py         # community tables (posts, comments, likes)
python migrate_community_timeframe.py # community post timeframe field
python migrate_credits.py           # credit tables (user_credits, credit_transactions, payment_orders)
python migrate_kakao_refresh.py     # kakao_refresh_token field
python migrate_allowed_timeframes.py # allowed timeframes per strategy
python migrate_system_settings.py   # system_settings table
python migrate_telegram.py          # telegram_chat_id field
python migrate_kakao_encrypt.py     # kakao token Fernet encryption migration
python migrate_notifications.py     # notification_trade/bot_status/system fields
python migrate_exchange_field.py    # exchange_name field on bot_configs
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
| GET | `/auth/me` | Current user info (includes notification settings) |
| GET | `/auth/notifications` | 현재 알림 설정 조회 (trade/bot_status/system) |
| PUT | `/auth/notifications` | 알림 설정 업데이트 |

### Bots (`/bot`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/bot/active` | 현재 실행 중인 봇 목록 (공개, 인증 불필요, 닉네임 마스킹) |
| POST | `/bot/` | Create new bot config (max 5/user, live max 1/user) |
| PUT | `/bot/{bot_id}` | Update bot config (stopped state only) |
| DELETE | `/bot/{bot_id}` | Delete bot + related data (stopped state only) |
| POST | `/bot/start/{bot_id}` | Start async trading bot (거래소별 잔고 검증) |
| POST | `/bot/stop/{bot_id}` | Stop bot (warns about live positions) |
| GET | `/bot/status/{bot_id}` | Running/Stopped status |
| GET | `/bot/logs/{bot_id}` | Trade log history (last 100) |
| GET | `/bot/performance/{bot_id}` | 봇 성과 통계 (총 PnL, 승률, 최대 드로다운, 일별/주별 PnL) |
| GET | `/bot/list` | List current user's bots |

### Keys (`/keys`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/keys/` | Add/update exchange API key (Fernet encrypted) |
| GET | `/keys/` | List saved keys (preview only) |
| GET | `/keys/balance` | Fetch exchange account balances via CCXT (Upbit/Bithumb) |

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
| GET | `/admin/dashboard` | 관리자 대시보드 통계 (유저/봇/거래/매출/시스템 헬스) |
| GET | `/admin/users` | List all users (admin only) |
| GET | `/admin/users/pending` | List pending approval users (admin only) |
| POST | `/admin/users/{user_id}/approve` | Approve user (set is_active=True) |
| POST | `/admin/users/{user_id}/reject` | Reject user (set is_active=False) |

### Credits (`/credits`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/credits/` | Current user's credit balance |
| GET | `/credits/history` | Credit transaction history (paginated, filterable by tx_type) |
| POST | `/credits/payment/order` | Create Toss Payments order for credit purchase |
| POST | `/credits/payment/confirm` | Confirm Toss payment and charge credits (1 KRW = 1 credit) |
| GET | `/credits/payment/history` | Payment order history |
| GET | `/credits/admin/overview` | Admin: all users' credit overview (admin only) |
| POST | `/credits/admin/{user_id}/adjust` | Admin: manually adjust user credits (admin only) |

### Community (`/community`)
| Method | Path | Description |
|--------|------|-------------|
| PUT | `/community/profile/nickname` | Update nickname (2-20 chars, unique) |
| PUT | `/community/profile/telegram` | 텔레그램 Chat ID 연동 |
| DELETE | `/community/profile/telegram` | 텔레그램 연동 해제 |
| POST | `/community/profile/telegram/test` | 텔레그램 알림 테스트 전송 |
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
| GET | `/community/leaderboard` | 봇별 수익률 리더보드 (공개, period: all/monthly/weekly, 최소 5건 이상) |
| GET | `/community/strategy-rankings` | 전략별 평균 성과 요약 (공개) |
| GET | `/community/strategies/{strategy_name}/reviews` | Get strategy reviews (filterable by timeframe) |
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
- **Atomic position saves**: `position_manager.py` uses `begin_nested()` savepoint for crash-safe delete+insert
- **Graceful shutdown**: `graceful_shutdown()` cancels all tasks with timeout, preserving positions in DB
- **Auto-recovery**: `recover_active_bots()` restores bots marked `is_active=True` on server startup
- **Lifespan events**: `main.py` uses `asynccontextmanager` lifespan for startup recovery + shutdown
- **Bot limits**: Max 5 bots/user total, max 1 live (실매매) bot/user, unlimited paper (모의투자) bots
- **TOCTOU-safe dict access**: All `active_bots` access uses `.get()` pattern to prevent KeyError in async context
- **Stop cleanup**: `stop_bot` lets the task's `finally` block handle `active_bots` cleanup (no early pop)

### 4. Rate Limiting
`backend/main.py` uses `slowapi` for rate limiting. Auth endpoints are limited to 10 requests/minute per IP.

### 5. Fernet Encryption for API Keys & Tokens
`backend/crypto_utils.py` — provides `encrypt_key()` / `decrypt_key()` using Fernet symmetric encryption.
Requires `FERNET_KEY` environment variable. All exchange API key storage uses this module.
- **Token encryption**: `encrypt_token()` / `decrypt_token()` for Kakao OAuth tokens (idempotent, skips already-encrypted values)
- **Exchange factory**: `create_exchange(exchange_name, api_key, api_secret)` creates ccxt instances for upbit/bithumb
- **Encryption detection**: `is_fernet_encrypted()` checks for Fernet prefix to prevent double-encryption

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

### 9. User Registration (Auto-Approve)
New users register with `is_active=True` (auto-approved). Kakao 가입 시 크레딧 보너스 1000 자동 지급.
Admin panel still exists for user management (비활성화/크레딧 조정 등).

### 10. Dependency Injection
`backend/dependencies.py` — provides:
- `get_db()` — yields DB session
- `get_current_user()` — validates JWT, checks `is_active`
- `get_current_user_optional()` — returns `None` if no valid token (for public routes)
- `get_admin_user()` — validates JWT + checks `is_admin`

### 11. Frontend API Client
`frontend/src/lib/api.ts` — Axios instance that automatically attaches JWT from localStorage.
All API calls must go through this client, never fetch directly.
- **401 deduplication**: `isRedirecting` flag prevents cascading login redirects during polling
- **Bot status resilience**: Dashboard preserves previous bot status on API failure (merge, not replace)

### 12. Credit System & Performance-Based Fees
`backend/credit_service.py` — core credit business logic.
- **Signup bonus**: 1000 credits on admin approval
- **Profit fee**: 10% of real-trade profit deducted as platform fee
- **Loss refund**: 10% of real-trade loss refunded as credits
- **Credit purchase**: Toss Payments v1 SDK integration (API 개별 연동 키, 1 KRW = 1 credit)
- **Bot start check**: Live bots require sufficient credits (`check_sufficient_credits()`)
- **Thread-safe**: Uses `database.get_db_session()` context manager for bot_manager calls
- **Atomic transactions**: Credit balance + transaction log updated in same DB session
- **Row-level locking**: `with_for_update()` on credit balance to prevent concurrent PnL race conditions

### 13. Frontend Constants
`frontend/src/lib/constants.ts` — centralized strategy lists, symbol lists, timeframes, exchanges, and poll intervals.
Separate `STRATEGIES` (for backtest) and `BOT_STRATEGIES` (for bot creation) lists.
`EXCHANGES` array for exchange selection (upbit, bithumb).
Derived constants: `TIMEFRAME_LABEL_MAP`, `BACKTEST_TIMEFRAMES`, `CHART_COLORS`, `LIVE_BOTS_POLL_INTERVAL_MS`, `BOT_TO_BACKTEST_STRATEGY`.
Components import label maps directly from constants instead of receiving them as props.

### 14. Backend Constants
`backend/constants.py` — centralized trading parameters and configuration values.
Includes `STRATEGY_LABELS` (Korean display names), data fetcher tuning (`FETCH_CHUNK_SIZE_*`, `FETCH_MAX_RETRIES`, `FETCH_BACKOFF_MAX_SECONDS`, `DB_SAVE_CHUNK_SIZE`).

### 15. Common Utilities
`backend/utils.py` — shared helper functions to eliminate duplication:
- `safe_json_loads()` — safe JSON parsing with fallback default
- `parse_symbols()` — comma-separated symbol string to list
- `mask_nickname()` — anonymize user nicknames (첫 글자 + **)

### 16. Exchange Factory Pattern
`backend/crypto_utils.py` — `create_exchange(exchange_name, api_key, api_secret)` returns a configured ccxt exchange instance.
Supports `upbit` and `bithumb`. All exchange instantiation must go through this factory (never create ccxt instances directly).
Bot start validation uses the factory to fetch balances from the user's selected exchange.

### 17. Error Monitoring (TelegramErrorHandler)
`backend/error_monitor.py` — custom `logging.Handler` that sends ERROR+ level logs to Telegram admin chat.
- **Rate limiting**: Same error key (module + message prefix) suppressed for 60 seconds
- **Non-blocking**: Uses `asyncio.create_task()` or background thread for sending
- **Infinite loop prevention**: Ignores errors from `notifications` module and `httpx`
- **Memory safety**: Auto-cleans `_last_sent` dict when entries exceed 1000

### 18. Category-Based Notification System
`backend/notifications.py` — per-user notification preferences with category filtering.
- `send_trade_notification(user_id, message)` — checks `notification_trade` setting
- `send_bot_status_notification(user_id, message)` — checks `notification_bot_status` setting
- `send_system_notification(message)` — always sends to admin chat (no user setting check)
- Each function checks user's DB preference before sending via Telegram

### 19. PWA Support
Frontend implements Progressive Web App capabilities:
- `frontend/public/manifest.json` — app manifest (name, icons, theme color, display mode)
- `frontend/public/sw.js` — service worker for offline caching
- `frontend/public/icons/` — PWA icons (192/512, maskable, apple-touch)
- `frontend/src/components/ServiceWorkerRegistration.tsx` — SW registration component

### 20. Onboarding Guide
`frontend/src/components/OnboardingGuide.tsx` — step-by-step onboarding for first-time users.
Guides through: API key registration -> backtest -> bot creation.

### 21. Auth Context
`frontend/src/contexts/AuthContext.tsx` — React context providing `useAuth()` hook.
Centralizes auth state (user, login, logout) with localStorage JWT management.

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
4. **~~No test suite~~** — **FIXED.** `backend/tests/` contains core logic unit tests (credit, bot, position). Uses pytest with DB fixtures.
5. **~~Kakao tokens stored in DB~~** — **FIXED.** `crypto_utils.encrypt_token()` / `decrypt_token()` now encrypts kakao tokens with Fernet. Migration: `migrate_kakao_encrypt.py`.
6. **~~TOCTOU race conditions~~** — **FIXED.** `bot_manager.py` and `routers/bots.py` now use `.get()` pattern for all `active_bots` dict access.
7. **~~Bot stop race condition~~** — **FIXED.** `stop_bot` no longer pops from `active_bots`; lets task's `finally` block handle cleanup.
8. **~~Non-atomic position persistence~~** — **FIXED.** `position_manager.py` uses `begin_nested()` savepoint for crash-safe saves.
9. **~~Credit concurrent update~~** — **FIXED.** `credit_service.py` uses `with_for_update()` row-level lock.
10. **Error monitoring** — `backend/error_monitor.py` `TelegramErrorHandler` sends ERROR+ logs to admin Telegram with rate limiting.

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

## Business Information

- **상호**: 플레이위드
- **대표**: 주은오
- **사업자등록번호**: 880-58-00862
- **소재지**: 서울특별시 영등포구 경인로 882, 1103호(영등포동1가, 여의도씨티아이)
- **업태**: 정보통신업 / 응용 소프트웨어 개발 및 공급업
- **이메일**: seal5945@gmail.com
- **호스팅**: Amazon Web Services (AWS)

### Legal Pages
- **이용약관**: `/terms` — 투자 위험 고지, 면책조항, API 키 보안 안내
- **개인정보처리방침**: `/privacy` — PIPA 준수, 수집 항목, 보유 기간, 위탁 업체, 보호책임자
- **랜딩 페이지 푸터**: 사업자 정보 + 투자 위험 고지 + 약관/방침 링크

### Notifications
- **Telegram**: 카테고리별 알림 시스템 (매매 체결/봇 상태/시스템), per-user Telegram 연동 (`User.telegram_chat_id`)
- **알림 설정**: 사용자별 on/off 제어 (`notification_trade`, `notification_bot_status`, `notification_system`)
- **에러 모니터링**: ERROR 이상 로그 자동 텔레그램 전송 (`TelegramErrorHandler`)
- Kakao Talk notifications 제거됨 (talk_message scope 삭제)

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
- Toast notifications via `useToast()` hook from `components/ui/Toast.tsx` — replaces browser `alert()`
- Delete confirmations via `DeleteConfirmationModal` — replaces browser `confirm()`
- General confirmations via `ConfirmationModal` — for non-delete actions
- Reusable UI components in `frontend/src/components/ui/` (ModalWrapper, ModalHeader, Button, Badge, Toast, etc.)
- All modals use `ModalWrapper` + `ModalHeader` from `components/ui/ModalWrapper.tsx`
- Label maps (`TIMEFRAME_LABEL_MAP`, `getStrategyLabel`, `CHART_COLORS`) centralized in `constants.ts`
- Type definitions in `frontend/src/types/` — API layer re-exports via `export type { X } from '@/types/...'`

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
curl -X POST https://backtested.bot/api/backtest/ \
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
| `recharts` | 차트 라이브러리 (수익률/PnL 시각화) |
| `tailwindcss` | CSS utility framework |
| `@tosspayments/payment-sdk` | Toss Payments v1 PG SDK (API 개별 연동 키 사용) |

---

## Improvement Roadmap (전략 개발 제외)

### P0 — 안정성/보안
- [x] **자동화 테스트**: 핵심 로직 단위 테스트 (`backend/tests/test_core_logic.py` — 크레딧 차감, 봇 시작/정지, 포지션 저장)
- [x] **카카오 토큰 암호화**: `encrypt_token()` / `decrypt_token()` Fernet 암호화 적용 (`migrate_kakao_encrypt.py`)
- [x] **에러 모니터링**: `TelegramErrorHandler` — ERROR 이상 로그를 텔레그램으로 관리자 전송 (`backend/error_monitor.py`)
- [x] **DB 백업 검증**: AWS RDS 백업 정책 검증 스크립트 (`backend/scripts/check_rds_backup.py`)

### P1 — 사용자 경험
- [x] **온보딩 가이드**: `OnboardingGuide.tsx` — 첫 방문 시 단계별 안내 (API 키 등록 → 백테스트 → 봇 생성)
- [x] **봇 성과 대시보드**: `GET /bot/performance/{bot_id}` + `dashboard/performance/page.tsx` — 수익률 차트(recharts), 일별/주별 PnL, 최대 드로다운
- [x] **알림 세분화**: `notification_trade/bot_status/system` 필드 + `GET/PUT /auth/notifications` — 카테고리별 on/off 설정
- [x] **모바일 최적화**: PWA 지원 (`manifest.json`, `sw.js`, `ServiceWorkerRegistration.tsx`, 홈화면 추가, 오프라인 캐시)

### P2 — 확장성/편의
- [x] **관리자 대시보드 강화**: `GET /admin/dashboard` — 전체 봇 현황, 매출 통계, 시스템 헬스 모니터링
- [x] **커뮤니티 활성화**: `GET /community/leaderboard` + `GET /community/strategy-rankings` — 전략 랭킹, 수익률 리더보드
- [ ] **다국어 지원**: 영어 UI (해외 사용자 대비)
- [x] **거래소 확장**: 빗썸 추가 (`create_exchange()` factory, `EXCHANGES` 상수, `exchange_name` 필드)
