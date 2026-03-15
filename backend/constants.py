"""
constants.py - 프로젝트 전역 상수 정의

모든 매직 넘버와 설정 상수를 한 곳에서 관리합니다.
비즈니스 로직이나 트레이딩 전략 파라미터는 포함하지 않습니다.
(전략 파라미터는 core/config.py 참조)
"""

import re

# ──────────────────────────────────────────────
# 봇 제한 (Bot Limits)
# ──────────────────────────────────────────────
MAX_BOTS_PER_USER: int = 5           # 사용자당 최대 봇 수
MAX_LIVE_BOTS_PER_USER: int = 1      # 실매매 봇은 사용자당 최대 1개

# ──────────────────────────────────────────────
# 입력값 검증 (Validation)
# ──────────────────────────────────────────────
# 심볼 형식 검증 (예: BTC/KRW, ETH/USDT)
SYMBOL_PATTERN: re.Pattern = re.compile(r'^[A-Z0-9]{2,10}/[A-Z]{3,5}$')

# 허용되는 타임프레임
VALID_TIMEFRAMES: set[str] = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "12h",
    "1d", "1w",
}

# ──────────────────────────────────────────────
# 리스크 관리 (Risk Management)
# ──────────────────────────────────────────────
MAX_CONCURRENT_POSITIONS: int = 3        # 최대 동시 포지션 수
MAX_RISK_MULTIPLIER: float = 2.0         # 리스크 배수 상한 (자산 대비 최대 4%)
STOP_LOSS_COOLDOWN_SECONDS: int = 3600   # 손절 후 재진입 금지 시간 (1시간)

# ──────────────────────────────────────────────
# 주문 실행 (Execution)
# ──────────────────────────────────────────────
# 페이퍼 트레이딩 슬리피지 (0.05% ~ 0.15%)
PAPER_SLIPPAGE_MIN: float = 0.0005
PAPER_SLIPPAGE_MAX: float = 0.0015

# 실매매 재시도 설정
MAX_RETRIES: int = 3
RETRY_DELAY: int = 2  # seconds

# ──────────────────────────────────────────────
# 봇 루프 (Bot Loop)
# ──────────────────────────────────────────────
MAX_CONSECUTIVE_ERRORS: int = 10  # 연속 에러 시 봇 중단 임계값

# ──────────────────────────────────────────────
# 크레딧 시스템 (Credit System)
# ──────────────────────────────────────────────
CREDIT_SIGNUP_BONUS: float = 1000.0        # 가입 시 지급 크레딧
CREDIT_PROFIT_FEE_RATE: float = 0.10       # 수익의 10% 수수료
CREDIT_LOSS_REFUND_RATE: float = 0.10      # 손실의 10% 환불

# ──────────────────────────────────────────────
# 결제 (Payment)
# ──────────────────────────────────────────────
MIN_CHARGE_AMOUNT: int = 1000              # 최소 충전 금액 (원)
MAX_CHARGE_AMOUNT: int = 1000000           # 최대 충전 금액 (원)
TOSS_CONFIRM_URL: str = "https://api.tosspayments.com/v1/payments/confirm"

# ──────────────────────────────────────────────
# 데이터 페칭 (Data Fetcher)
# ──────────────────────────────────────────────
FETCH_CHUNK_SIZE_UPBIT: int = 200          # Upbit API 1회 요청 최대 캔들 수
FETCH_CHUNK_SIZE_DEFAULT: int = 500        # 기타 거래소 1회 요청 최대 캔들 수
DB_SAVE_CHUNK_SIZE: int = 1000             # DB 벌크 저장 청크 크기
FETCH_MAX_RETRIES: int = 5                 # 레이트 리밋 재시도 최대 횟수
FETCH_BACKOFF_MAX_SECONDS: int = 30        # 재시도 대기 최대 시간 (초)

# ──────────────────────────────────────────────
# 거래소 라벨 (Exchange Labels)
# ──────────────────────────────────────────────
EXCHANGE_LABELS: dict[str, str] = {
    'upbit': '업비트 (Upbit)',
    'bithumb': '빗썸 (Bithumb)',
}

# ──────────────────────────────────────────────
# 전략 라벨 (Strategy Labels) — 알림용
# ──────────────────────────────────────────────
STRATEGY_LABELS: dict[str, str] = {
    # Original
    'steady_compounder': '스테디 복리',
    'steady_compounder_v1': '스테디 복리 V1',
    'momentum_breakout_pro_stable': '모멘텀 안정형',
    'james_pro_stable': '모멘텀 안정형',
    'momentum_stable': '모멘텀 안정형',
    'momentum_breakout_pro_aggressive': '모멘텀 공격형',
    'james_pro_aggressive': '모멘텀 공격형',
    'momentum_aggressive': '모멘텀 공격형',
    'momentum_breakout_elite': '모멘텀 엘리트',
    'james_pro_elite': '모멘텀 엘리트',
    'momentum_elite': '모멘텀 엘리트',
    'momentum_breakout_basic': '모멘텀 기본',
    # Timeframe-optimized (성능 검증 통과 8개)
    'momentum_basic_1d': '모멘텀 기본 (1일)',
    'momentum_stable_1h': '모멘텀 안정형 (1시간)',
    'momentum_stable_1d': '모멘텀 안정형 (1일)',
    'momentum_aggressive_1h': '모멘텀 공격형 (1시간)',
    'momentum_aggressive_4h': '모멘텀 공격형 (4시간)',
    'momentum_aggressive_1d': '모멘텀 공격형 (1일)',
    'momentum_elite_1d': '모멘텀 엘리트 (1일)',
    'steady_compounder_4h': '스테디 복리 (4시간)',
}

# ──────────────────────────────────────────────
# 전략 정의 (Strategy Definitions)
# ──────────────────────────────────────────────
# is_public: 일반 사용자에게 공개 여부 (관리자는 항상 전체 표시)
# DB 설정(strategy_visibility)으로 오버라이드 가능
STRATEGY_DEFINITIONS: list[dict] = [
    {"value": "momentum_breakout_basic", "label": "모멘텀 돌파 (기본)", "is_public": True},
    {"value": "momentum_breakout_pro_stable", "label": "모멘텀 돌파 Pro (안정형)", "is_public": True},
    {"value": "momentum_breakout_pro_aggressive", "label": "모멘텀 돌파 Pro (공격형)", "is_public": True},
    {"value": "momentum_breakout_elite", "label": "모멘텀 돌파 Elite", "is_public": True},
    {"value": "steady_compounder", "label": "스테디 복리 (주간 안정형)", "is_public": True},
    {"value": "steady_compounder_v1", "label": "스테디 복리 V1 (백업)", "is_public": False},
    # Timeframe-optimized (성능 검증 통과 8개)
    {"value": "momentum_basic_1d", "label": "모멘텀 기본 (1일)", "is_public": True},
    {"value": "momentum_stable_1h", "label": "모멘텀 안정형 (1시간)", "is_public": True},
    {"value": "momentum_stable_1d", "label": "모멘텀 안정형 (1일)", "is_public": True},
    {"value": "momentum_aggressive_1h", "label": "모멘텀 공격형 (1시간)", "is_public": True},
    {"value": "momentum_aggressive_4h", "label": "모멘텀 공격형 (4시간)", "is_public": True},
    {"value": "momentum_aggressive_1d", "label": "모멘텀 공격형 (1일)", "is_public": True},
    {"value": "momentum_elite_1d", "label": "모멘텀 엘리트 (1일)", "is_public": True},
    {"value": "steady_compounder_4h", "label": "스테디 복리 (4시간)", "is_public": True},
]

# 백테스트 전용 별칭 (james_* 시리즈)
BACKTEST_STRATEGY_ALIASES: list[dict] = [
    {"value": "james_basic", "label": "모멘텀 돌파 (기본)", "maps_to": "momentum_breakout_basic"},
    {"value": "james_pro_stable", "label": "모멘텀 돌파 Pro (안정형)", "maps_to": "momentum_breakout_pro_stable"},
    {"value": "james_pro_aggressive", "label": "모멘텀 돌파 Pro (공격형)", "maps_to": "momentum_breakout_pro_aggressive"},
    {"value": "james_pro_elite", "label": "모멘텀 돌파 PRO (초고수익형)", "maps_to": "momentum_breakout_elite"},
]
