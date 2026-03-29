# CLAUDE.md — AI Assistant Guide for Backtested

## Project Overview

**Backtested** (backtested.bot) — 알고리즘 트레이딩 시뮬레이션 + 커뮤니티 플랫폼
- **Backend:** FastAPI (Python 3.12) + PostgreSQL (AWS RDS)
- **Frontend:** Next.js 14 (TypeScript) + Tailwind CSS
- **Infrastructure:** Docker Compose, Nginx (SSL), GitHub Actions CI/CD
- **Exchange:** Upbit/Bithumb via CCXT (관리자 실매매 전용)
- **Auth:** Kakao OAuth 2.0 + JWT
- **Production URL:** https://backtested.bot

---

## Service Model

- **일반 사용자**: 모의투자 봇 1개 + 백테스트 + 커뮤니티 + 텔레그램 알림
- **관리자**: 실매매 봇 + API 키 관리 + 거래소 잔고 조회 + 사용자 관리 + 전략 가시성 설정
- 실매매/API 키는 프론트/백엔드 양쪽에서 `is_admin` 체크

---

## Key Architecture

### Routers (8개)
`auth`, `backtest`, `bots`, `keys`, `admin`, `community`, `settings` (전략 가시성), `strategies` (커스텀 전략 CRUD)

### Models (13개)
`User`, `ExchangeKey`, `BotConfig`, `TradeLog`, `OHLCV`, `BacktestHistory`, `ActivePosition`, `UserStrategy`, `CommunityPost`, `PostComment`, `PostLike`, `ChatMessage`, `SystemSettings`

### Strategy System (21개 전략)
- `backend/core/strategies/`에 위치, `strategy.py`의 `get_strategy(name)` 팩토리
- 카테고리: 모멘텀(Basic/Stable/Aggressive), 멀티시그널, 퀵스윙, 트렌드라이더, 와이드스윙, 스캘퍼, 추세추종
- 타임프레임: 15m, 1h, 4h, 1d
- 상태: `confirmed` (공개) / `testing` (관리자만)
- DB-driven visibility override via `SystemSettings`

### User Custom Strategies
- 백테스트 결과에서 파라미터 저장 → `UserStrategy` 모델
- `BotConfig.custom_strategy_id`로 참조, `routers/strategies.py`에서 CRUD

### Bot Manager (`bot_manager.py`)
- `Dict[int, asyncio.Task]` 기반 비동기 봇 생명주기
- **60초 루프**: 전 종목 fetch + SL/TP 청산 감시 + 신호 분석
- **텔레그램 피드백**: 캔들 타임스탬프 기반 — `df.iloc[-2]` 타임스탬프 변경 시(새 봉 마감) 전송
- **트리거 조건**: `"조건이름: 실제값 부등호 비교값"` 포맷
- `feedback_formatter.py` — 메시지 포맷팅, `trade_logger.py` — DB 거래 기록
- `position_manager.py` — atomic position persistence (`begin_nested()` savepoint)
- Auto-recovery on server restart
- Limits: 일반 1개, 관리자 5개(실매매 1개)

### Encryption & Notifications
- `crypto_utils.py` — Fernet 암복호화 + `create_exchange()` 팩토리
- `notifications.py` — 카테고리별 텔레그램 알림 (trade, bot_status, system)
- `error_monitor.py` — ERROR+ 로그 → 관리자 텔레그램 (rate limiting)

---

## Critical Rules

- **전략 로직 수정 금지**: 기존 전략의 신호 로직은 검증 완료. 파라미터/인프라 변경만 허용
- **bot_manager.py limit=300**: 전략은 `current_idx >= 200` 필요
- **새 전략 추가**: `strategies/` 클래스 → `strategy.py` STRATEGY_MAP → `constants.py` STRATEGY_DEFINITIONS → `constants.ts`
- **SL/TP 통일**: `backtest_sl_pct`/`backtest_tp_pct`/`backtest_trailing` — 백테스트와 실매매 동일
- **로그인 리다이렉트**: `/login?redirect=/path` 지원 — AuthGuard에서 자동 전달

---

## Code Conventions

### Python (Backend)
- Type hints, `async def` route handlers
- `Depends(get_current_user)` / `Depends(get_admin_user)`
- Config: `settings.py`, 암호화: `crypto_utils.py`
- Korean comments OK

### TypeScript (Frontend)
- Functional components + hooks only
- API: `lib/api.ts` (Axios) + `lib/api/` modular modules
- Constants: `lib/constants.ts` (21개 전략 + helpers)
- Hooks: `lib/useStrategies.ts` 등
- `@/` path alias → `src/`, Tailwind CSS
- **테마 토큰 필수**: `text-white`/`text-gray-*` 금지 → `text-th-text`/`text-th-text-secondary`/`text-th-text-muted` 사용
- **배경/보더**: `bg-th-card`, `bg-th-modal`, `bg-th-input`, `border-th-border`, `border-th-border-light`
- **하드코딩 hex 금지**: `bg-[#0d1117]` 등 금지 → CSS 변수 토큰 사용
- **에러 처리**: catch 블록에서 `toast.error()` 필수 (폴링 제외), console.error 금지
- **반응형 텍스트**: `text-[10px] sm:text-xs` 패턴 — 10-11px에는 반드시 sm 브레이크포인트 추가
- **디자인 컨텍스트**: `.impeccable.md` 참조 (브랜드, 팔레트, 원칙)

### Git
- Production branch: `main`, push 시 자동 배포

---

## CI/CD

`.github/workflows/deploy.yml` — Build(GitHub Actions) → GHCR push → SSH deploy
- **서버 RAM 414MB** → Next.js 빌드는 CI에서 수행
- Secrets: `SERVER_IP`, `SERVER_USERNAME`, `SSH_PRIVATE_KEY`, `GHCR_PAT`

---

## Business Info

플레이위드 | 대표 주은오 | 사업자 880-58-00862 | seal5945@gmail.com
서울시 영등포구 경인로 882, 1103호 | 호스팅: AWS
