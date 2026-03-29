# CLAUDE.md — AI Assistant Guide for Backtested

## Project Overview

**Backtested** (backtested.bot) is a full-stack algorithmic trading simulation platform with community features.
- **Backend:** FastAPI (Python 3.12) with PostgreSQL (AWS RDS)
- **Frontend:** Next.js 14 (TypeScript) with Tailwind CSS
- **Infrastructure:** Docker Compose, Nginx (SSL), GitHub Actions CI/CD
- **Exchange:** Upbit/Bithumb via CCXT library (관리자 실매매 전용)
- **Auth:** Kakao OAuth 2.0 + JWT (가입 즉시 로그인 가능)
- **Service Model:** 일반 사용자는 모의투자 봇 1개 + 알림, 관리자만 실매매 + API 키 관리
- **Production URL:** https://backtested.bot

---

## Repository Structure

```
backtested/
├── backend/                    # FastAPI Python application
│   ├── main.py                 # App entry point, CORS config, router registration, rate limiting
│   ├── models.py               # SQLAlchemy ORM models (13 models)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── database.py             # PostgreSQL connection (AWS RDS) with connection pooling
│   ├── settings.py             # Pydantic BaseSettings — centralized config from .env
│   ├── auth.py                 # JWT creation/verification helpers (reads from settings)
│   ├── dependencies.py         # FastAPI Depends() providers (get_db, get_current_user, get_admin_user)
│   ├── bot_manager.py          # Async bot task lifecycle management
│   ├── notifications.py        # Telegram bot notifications (카테고리별: trade, bot_status, system)
│   ├── error_monitor.py        # TelegramErrorHandler — ERROR 이상 로그를 텔레그램으로 관리자 전송
│   ├── crypto_utils.py         # Fernet encryption/decryption + API key masking + create_exchange() factory
│   ├── kakao_service.py        # Kakao OAuth token exchange & user info
│   ├── utils.py                # Common helpers (safe_json_loads, parse_symbols, mask_nickname)
│   ├── constants.py            # Centralized constants (bot limits, validation, strategy labels/definitions)
│   ├── log_config.py           # Centralized logging setup
│   ├── position_manager.py     # DB-based position persistence (atomic save/load/clear)
│   ├── feedback_formatter.py   # Telegram 피드백 메시지 포맷팅 (bot_manager에서 분리)
│   ├── trade_logger.py         # Trade logging — DB 거래 기록 영속화
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── migrations/             # DB migration scripts (16개)
│   ├── scripts/                # Utility scripts (batch backtest, comparison, RDS backup check)
│   ├── tests/
│   │   ├── conftest.py         # Test fixtures
│   │   └── test_core_logic.py  # 핵심 로직 단위 테스트
│   ├── routers/
│   │   ├── auth.py             # Kakao OAuth, JWT, 알림 설정, 회원 탈퇴
│   │   ├── backtest.py         # Backtest CRUD + share to community
│   │   ├── bots.py             # Bot CRUD + start/stop/status/logs/performance
│   │   ├── keys.py             # Exchange key management (관리자 전용)
│   │   ├── admin.py            # Admin: dashboard stats, user listing
│   │   ├── community.py        # Community: posts, comments, likes, chat, leaderboard, strategy reviews
│   │   ├── settings.py         # 전략 가시성 토글 + 백테스트 설정 관리
│   │   └── strategies.py       # 사용자 커스텀 전략 CRUD (백테스트→전략 저장)
│   └── core/
│       ├── config.py           # Trading parameters
│       ├── data_fetcher.py     # CCXT OHLCV fetcher with PostgreSQL caching
│       ├── execution.py        # Paper/live trade execution engine
│       ├── strategy.py         # Strategy factory: get_strategy(name)
│       ├── vector_backtester.py # Vectorized backtesting with vectorbt
│       └── strategies/         # 21개 전략 클래스 (base.py + 개별 전략)
├── frontend/                   # Next.js 14 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Landing page
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   ├── terms/page.tsx
│   │   │   ├── privacy/page.tsx
│   │   │   ├── auth/kakao/page.tsx
│   │   │   ├── auth/register-email/page.tsx
│   │   │   ├── community/      # Public community pages
│   │   │   └── dashboard/
│   │   │       ├── layout.tsx   # Sidebar navigation
│   │   │       ├── page.tsx     # Bot control + trade log viewer
│   │   │       ├── backtest/page.tsx
│   │   │       ├── keys/page.tsx       # API 키 관리 (관리자만 접근)
│   │   │       ├── performance/page.tsx
│   │   │       ├── live-bots/page.tsx   # 실시간 봇 현황 대시보드
│   │   │       ├── profile/page.tsx     # 사용자 프로필
│   │   │       ├── settings/page.tsx
│   │   │       ├── admin/page.tsx
│   │   │       └── community/          # Dashboard community pages
│   │   │           └── profile/page.tsx # 커뮤니티 멤버 프로필
│   │   ├── contexts/AuthContext.tsx
│   │   ├── components/
│   │   │   ├── ui/              # Reusable UI (ThemeToggle, Badge, StatCard, PageContainer 등)
│   │   │   ├── modals/          # BotFormModal, ConfirmationModal, DeleteConfirmationModal, AssetDetailModal
│   │   │   ├── cards/BotCard.tsx
│   │   │   └── sections/        # SummaryStats, TradeLogTimeline
│   │   ├── types/               # TypeScript type definitions (index.ts + 모듈별)
│   │   └── lib/
│   │       ├── api.ts           # Axios instance with auth interceptors
│   │       ├── api/             # Modular API functions (9 modules)
│   │       │   ├── admin.ts
│   │       │   ├── auth.ts
│   │       │   ├── backtest.ts
│   │       │   ├── bot.ts
│   │       │   ├── community.ts
│   │       │   ├── keys.ts
│   │       │   ├── settings.ts  # 전략 가시성 + 백테스트 설정 API
│   │       │   ├── strategies.ts # 사용자 커스텀 전략 API
│   │       │   └── index.ts
│   │       ├── constants.ts     # 21개 전략 정의, symbols, timeframes, helper functions
│   │       ├── useStrategies.ts # 전략 관련 React hook
│   │       └── utils.ts
│   ├── public/                  # PWA manifest, icons, service worker
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── .github/workflows/deploy.yml  # CI/CD: build → GHCR → deploy
```

---

## Development Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py              # starts uvicorn on port 8000
```

Environment variables (see `backend/.env.example`):
- `KAKAO_REST_API_KEY`, `KAKAO_REDIRECT_URI` — Kakao OAuth
- `SECRET_KEY` — JWT signing key
- `FERNET_KEY` — Fernet encryption key
- `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT`, `DB_NAME` — PostgreSQL
- `EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET` — 관리자 실매매용 (선택)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Telegram notifications

### Frontend

```bash
cd frontend
npm install
npm run dev                 # dev server on port 3000
```

### Full Stack (Docker Compose)

```bash
docker-compose pull && docker-compose up -d
```

---

## Database Models (`backend/models.py`)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `User` | id, email, nickname, kakao_id, telegram_chat_id, notification_*, is_active, is_admin, created_at | `is_active=True` (auto-approved); `is_admin` gates admin features |
| `ExchangeKey` | user_id, exchange_name, api_key_encrypted, api_secret_encrypted | Fernet 암호화, 관리자만 등록 가능 |
| `BotConfig` | user_id, symbol, timeframe, exchange_name, strategy_name, is_active, paper_trading_mode, allocated_capital, custom_strategy_id | 일반 사용자: 모의투자 1개, 관리자: 5개 (실매매 1개) |
| `TradeLog` | bot_id, symbol, side, price, amount, pnl, reason | BUY/SELL |
| `OHLCV` | symbol, timeframe, timestamp, open, high, low, close, volume | CCXT 캐싱 |
| `BacktestHistory` | user_id, symbols, timeframe, strategy_name, result_data, status, title | 백테스트 결과 |
| `ActivePosition` | bot_id, symbol, position_amount, entry_price, stop_loss, take_profit | 봇 포지션 영속화 |
| `UserStrategy` | user_id, name, base_strategy_name, custom_params (JSON), backtest_history_id, is_deleted | 사용자 커스텀 전략 (백테스트에서 생성) |
| `CommunityPost` | user_id, post_type, title, content, like_count, comment_count | 커뮤니티 |
| `PostComment` | post_id, user_id, content, is_deleted | Soft-delete |
| `PostLike` | post_id, user_id | Unique constraint |
| `ChatMessage` | user_id, content, created_at | 실시간 채팅 |
| `SystemSettings` | key, value | Key-value 시스템 설정 |

---

## API Routes

All routes except `/auth/*` and some `/community/*` GETs require `Authorization: Bearer <jwt>`.

### Auth (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/kakao` | Kakao OAuth → JWT |
| POST | `/auth/kakao/complete` | 이메일 없는 카카오 사용자 등록 완료 |
| GET | `/auth/me` | Current user info |
| GET/PUT | `/auth/notifications` | 알림 설정 조회/업데이트 |
| DELETE | `/auth/withdraw` | 회원 탈퇴 |

### Bots (`/bot`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/bot/active` | 실행 중인 봇 목록 (공개) |
| POST | `/bot/` | 봇 생성 (일반: 모의투자 1개, 관리자: 5개) |
| PUT | `/bot/{bot_id}` | 봇 설정 수정 (정지 상태만) |
| DELETE | `/bot/{bot_id}` | 봇 삭제 |
| POST | `/bot/start/{bot_id}` | 봇 시작 (실매매는 관리자만) |
| POST | `/bot/stop/{bot_id}` | 봇 정지 |
| GET | `/bot/status/{bot_id}` | Running/Stopped |
| GET | `/bot/logs/{bot_id}` | 거래 내역 |
| GET | `/bot/performance/{bot_id}` | 봇 성과 통계 |
| GET | `/bot/list` | 내 봇 목록 |

### Keys (`/keys`) — 관리자 전용
| Method | Path | Description |
|--------|------|-------------|
| POST | `/keys/` | API 키 등록/수정 |
| GET | `/keys/` | 등록된 키 목록 |
| GET | `/keys/balance` | 거래소 잔고 조회 |

### Backtest (`/backtest`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/backtest/` | 단일 심볼 백테스트 |
| POST | `/backtest/portfolio` | 포트폴리오 백테스트 |
| GET | `/backtest/status/{task_id}` | 진행 상태 |
| GET | `/backtest/history` | 백테스트 이력 |

### Community (`/community`)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/community/posts` | 게시글 목록/작성 |
| GET/POST | `/community/chat` | 실시간 채팅 |
| GET | `/community/leaderboard` | 수익률 리더보드 |
| GET | `/community/strategy-rankings` | 전략별 랭킹 |
| GET | `/community/strategies/{name}/reviews` | 전략 리뷰 조회 |
| POST | `/community/strategies/{name}/rating` | 전략 평점 등록 |
| PUT | `/community/profile/nickname` | 닉네임 변경 |
| PUT | `/community/profile/telegram` | 텔레그램 연동 |

### Settings (`/settings`) — 관리자 전용
| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/strategies` | 전략 목록 + 가시성 설정 |
| PUT | `/settings/strategies/visibility` | 전략 가시성 토글 |
| GET | `/settings/backtest` | 백테스트 설정 |
| PUT | `/settings/backtest` | 백테스트 설정 업데이트 |

### Strategies (`/strategies`) — 사용자 커스텀 전략
| Method | Path | Description |
|--------|------|-------------|
| POST | `/strategies/` | 커스텀 전략 생성 |
| POST | `/strategies/from-backtest/{history_id}` | 백테스트 결과에서 전략 생성 |
| GET | `/strategies/` | 내 커스텀 전략 목록 |
| DELETE | `/strategies/{strategy_id}` | 커스텀 전략 삭제 |

### Admin (`/admin`) — 관리자 전용
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/dashboard` | 대시보드 통계 |
| GET | `/admin/users` | 사용자 목록 |

---

## Key Architectural Patterns

### 1. Service Model (사용자 권한)
- **일반 사용자**: 모의투자 봇 1개 + 백테스트 + 커뮤니티 + 텔레그램 알림
- **관리자**: 실매매 봇 + API 키 관리 + 거래소 잔고 조회 + 사용자 관리 + 전략 가시성 설정
- 실매매/API 키는 프론트/백엔드 양쪽에서 `is_admin` 체크

### 2. Strategy System
`backend/core/strategy.py` — `get_strategy(name)` returns a strategy instance.

#### 전략 목록 (21개)
| 카테고리 | 전략 | 타임프레임 |
|---------|------|-----------|
| 모멘텀 Basic | momentum_basic_1h/4h/1d | 1h, 4h, 1d |
| 모멘텀 Stable | momentum_stable_1h/4h/1d | 1h, 4h, 1d |
| 모멘텀 Aggressive | momentum_aggressive_1h/4h/1d | 1h, 4h, 1d |
| 멀티시그널 | multi_signal_15m/1h/4h/1d | 15m, 1h, 4h, 1d |
| 퀵 스윙 | quick_swing_15m/1h | 15m, 1h |
| 트렌드 라이더 | trend_rider_4h_v1/v2/v3 | 4h |
| 와이드 스윙 | wide_swing_1d | 1d |
| 스캘퍼 | scalper_15m | 15m |
| 추세추종 | trend_follower_15m | 15m |
| 시그널 테스트 | signal_test_15m | 15m |

#### 전략 상태 시스템
- `status: "confirmed"` — 검증 완료, 사용자에게 공개
- `status: "testing"` — 테스트 중, 관리자만 접근 가능
- DB-driven visibility override via `SystemSettings` (관리자 전략 가시성 토글)

#### 새 전략 추가 절차
1. `backend/core/strategies/`에 클래스 생성
2. `strategy.py` STRATEGY_MAP에 등록
3. `constants.py` STRATEGY_DEFINITIONS에 추가
4. `frontend/src/lib/constants.ts`에 추가

### 3. User Custom Strategies
- 사용자가 백테스트 결과에서 파라미터를 저장하여 커스텀 전략 생성
- `UserStrategy` 모델로 영속화, `BotConfig.custom_strategy_id`로 참조
- `routers/strategies.py`에서 CRUD 제공

### 4. Async Bot Management & Position Persistence
`backend/bot_manager.py` — `Dict[int, asyncio.Task]` for bot lifecycle.
- **60초 루프**: 매 tick마다 전 종목 데이터 fetch + SL/TP 청산 감시 + 신호 분석
- **텔레그램 피드백**: 시계 기반이 아닌 **캔들 타임스탬프 기반** — `df.iloc[-2]` 타임스탬프가 바뀌면(새 봉 마감) 전송
- **트리거 조건 표시**: `"조건이름: 실제값 부등호 비교값"` 포맷 (예: `❌ 이전MACD≤시그널: 450,369 > 402,785`)
- **피드백 포맷팅**: `feedback_formatter.py`에서 메시지 구성 (bot_manager에서 분리)
- **거래 기록**: `trade_logger.py`로 DB 영속화
- Position persistence to `ActivePosition` table every tick
- Atomic saves via `position_manager.py` (`begin_nested()` savepoint)
- Auto-recovery on server restart
- Bot limits: `MAX_BOTS_PER_REGULAR_USER=1`, `MAX_BOTS_PER_USER=5` (admin), `MAX_LIVE_BOTS_PER_USER=1`

### 5. Fernet Encryption
`backend/crypto_utils.py` — API keys + Kakao tokens encrypted with Fernet.
`create_exchange()` factory for ccxt instances (upbit/bithumb).

### 6. Category-Based Notifications
`backend/notifications.py` — per-user Telegram alerts.
- `send_trade_notification()` — 매매 체결
- `send_bot_status_notification()` — 봇 상태
- `send_system_notification()` — 관리자 시스템 알림

### 7. Error Monitoring
`backend/error_monitor.py` — `TelegramErrorHandler` sends ERROR+ logs to admin Telegram with rate limiting.

---

## Trading Strategies

모든 전략은 `backend/core/strategies/`에 위치. 진입: `check_buy_signal()`, 청산: 고정 SL/TP 또는 트레일링 스탑.

### SL/TP 통일 원칙
- `backtest_sl_pct`/`backtest_tp_pct`/`backtest_trailing` — 백테스트와 실매매 동일 로직
- 트레일링 모드: `backtest_trailing=True`, TP 없음 (추세 추종)

### Important Notes
- **전략 로직 수정 금지**: 기존 전략의 신호 로직은 검증 완료됨. 파라미터/인프라 변경만 허용.
- **bot_manager.py limit=300**: 전략은 `current_idx >= 200` 필요.
- **새 전략 추가**: `strategies/` 클래스 → `strategy.py` STRATEGY_MAP → `constants.py` STRATEGY_DEFINITIONS → `constants.ts` 추가

---

## CI/CD

**Workflow:** `.github/workflows/deploy.yml` (2-job pipeline)
1. **Build** (GitHub Actions): Docker images → GHCR push
2. **Deploy**: SSH → `docker compose pull` → `docker compose up -d --force-recreate`

**Why CI builds?** Server RAM 414MB; Next.js build requires 1GB+.

**Required GitHub Secrets:** `SERVER_IP`, `SERVER_USERNAME`, `SSH_PRIVATE_KEY`, `GHCR_PAT`

**To deploy:** push to `main`. Fully automated.

---

## Code Conventions

### Python (Backend)
- Type hints on all functions
- `async def` for route handlers
- `Depends(get_current_user)` for protected routes, `Depends(get_admin_user)` for admin routes
- All config via `settings.py`, encryption via `crypto_utils.py`
- Korean comments acceptable

### TypeScript (Frontend)
- Functional components + hooks only
- All API calls via `lib/api.ts` (Axios) + `lib/api/` modular modules
- Constants in `lib/constants.ts` (21개 전략 정의 + helper functions)
- Custom hooks in `lib/` (예: `useStrategies.ts`)
- `@/` path alias → `src/`
- Tailwind CSS, Toast notifications, ModalWrapper for modals

### Git
- Production branch: `main`
- CI/CD deploys automatically from `main`

---

## Business Information

- **상호**: 플레이위드
- **대표**: 주은오
- **사업자등록번호**: 880-58-00862
- **소재지**: 서울특별시 영등포구 경인로 882, 1103호
- **업태**: 정보통신업 / 응용 소프트웨어 개발 및 공급업
- **이메일**: seal5945@gmail.com
- **호스팅**: AWS

### Legal Pages
- **이용약관**: `/terms` — 투자 위험 고지, 면책조항
- **개인정보처리방침**: `/privacy` — PIPA 준수
