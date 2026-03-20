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
MAX_BOTS_PER_USER: int = 5           # 관리자 최대 봇 수
MAX_BOTS_PER_REGULAR_USER: int = 1   # 일반 사용자 최대 봇 수 (모의투자만)
MAX_LIVE_BOTS_PER_USER: int = 1      # 실매매 봇은 관리자만 최대 1개
MAX_USER_STRATEGIES: int = 10        # 사용자당 커스텀 전략 최대 수

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
    # Legacy aliases (하위 호환)
    'steady_compounder': '트렌드 라이더 (4시간)',
    'steady_compounder_v1': '트렌드 라이더 (4시간)',
    'steady_compounder_4h': '트렌드 라이더 (4시간)',
    'momentum_breakout_pro_stable': '모멘텀 안정형',
    'james_pro_stable': '모멘텀 안정형',
    'momentum_stable': '모멘텀 안정형',
    'momentum_breakout_pro_aggressive': '모멘텀 공격형',
    'james_pro_aggressive': '모멘텀 공격형',
    'momentum_aggressive': '모멘텀 공격형',
    'momentum_breakout_elite': '멀티시그널',
    'james_pro_elite': '멀티시그널',
    'momentum_elite': '멀티시그널',
    'momentum_breakout_basic': '모멘텀 기본',
    # Timeframe-optimized (15개 = 5 base × 3 TF)
    'momentum_basic_1h': '모멘텀 기본 (1시간)',
    'momentum_basic_4h': '모멘텀 기본 (4시간)',
    'momentum_basic_1d': '모멘텀 기본 (1일)',
    'momentum_stable_1h': '모멘텀 안정형 (1시간)',
    'momentum_stable_4h': '모멘텀 안정형 (4시간)',
    'momentum_stable_1d': '모멘텀 안정형 (1일)',
    'momentum_aggressive_1h': '모멘텀 공격형 (1시간)',
    'momentum_aggressive_4h': '모멘텀 공격형 (4시간)',
    'momentum_aggressive_1d': '모멘텀 공격형 (1일)',
    'momentum_elite_1h': '멀티시그널 (1시간)',
    'momentum_elite_4h': '멀티시그널 (4시간)',
    'momentum_elite_1d': '멀티시그널 (1일)',
    'multi_signal_1h': '멀티시그널 (1시간)',
    'multi_signal_4h': '멀티시그널 (4시간)',
    'multi_signal_1d': '멀티시그널 (1일)',
    'steady_compounder_1h': '퀵 스윙 (1시간)',
    'quick_swing_1h': '퀵 스윙 (1시간)',
    'trend_rider_4h': '트렌드 라이더 (4시간)',
    'trend_rider_4h_v1': '트렌드 라이더 V1 (4시간)',
    'trend_rider_4h_v2': '트렌드 라이더 V2 (4시간)',
    'steady_compounder_1d': '와이드 스윙 (1일)',
    'wide_swing_1d': '와이드 스윙 (1일)',
    # 15분봉 전략
    'scalper_15m': '스캘퍼 (15분)',
    'quick_swing_15m': '퀵 스윙 (15분)',
    'multi_signal_15m': '멀티시그널 (15분)',
    'trend_follower_15m': '추세추종 (15분)',
    'signal_test_15m': '매매 테스트 (15분)',
}

# ──────────────────────────────────────────────
# 전략 정의 (Strategy Definitions)
# ──────────────────────────────────────────────
# is_public: 일반 사용자에게 공개 여부 (관리자는 항상 전체 표시)
# DB 설정(strategy_visibility)으로 오버라이드 가능
# status: "confirmed" = 검증 완료 확정 전략, "testing" = 테스트 중인 전략
STRATEGY_DEFINITIONS: list[dict] = [
    {"value": "trend_rider_4h_v1", "label": "트렌드 라이더 V1 (4시간)", "is_public": True, "status": "confirmed"},
    {"value": "trend_rider_4h_v2", "label": "트렌드 라이더 V2 (4시간)", "is_public": True, "status": "confirmed"},
    {"value": "momentum_basic_1h", "label": "모멘텀 기본 (1시간)", "is_public": True, "status": "testing"},
    {"value": "momentum_basic_4h", "label": "모멘텀 기본 (4시간)", "is_public": True, "status": "testing"},
    {"value": "momentum_basic_1d", "label": "모멘텀 기본 (1일)", "is_public": True, "status": "testing"},
    {"value": "momentum_stable_1h", "label": "모멘텀 안정형 (1시간)", "is_public": True, "status": "testing"},
    {"value": "momentum_stable_4h", "label": "모멘텀 안정형 (4시간)", "is_public": True, "status": "testing"},
    {"value": "momentum_stable_1d", "label": "모멘텀 안정형 (1일)", "is_public": True, "status": "testing"},
    {"value": "momentum_aggressive_1h", "label": "모멘텀 공격형 (1시간)", "is_public": True, "status": "testing"},
    {"value": "momentum_aggressive_4h", "label": "모멘텀 공격형 (4시간)", "is_public": True, "status": "testing"},
    {"value": "momentum_aggressive_1d", "label": "모멘텀 공격형 (1일)", "is_public": True, "status": "testing"},
    {"value": "multi_signal_1h", "label": "멀티시그널 (1시간)", "is_public": True, "status": "testing"},
    {"value": "multi_signal_4h", "label": "멀티시그널 (4시간)", "is_public": True, "status": "testing"},
    {"value": "multi_signal_1d", "label": "멀티시그널 (1일)", "is_public": True, "status": "testing"},
    {"value": "quick_swing_1h", "label": "퀵 스윙 (1시간)", "is_public": True, "status": "testing"},
    {"value": "wide_swing_1d", "label": "와이드 스윙 (1일)", "is_public": True, "status": "testing"},
    {"value": "scalper_15m", "label": "스캘퍼 (15분)", "is_public": True, "status": "testing"},
    {"value": "quick_swing_15m", "label": "퀵 스윙 (15분)", "is_public": True, "status": "testing"},
    {"value": "multi_signal_15m", "label": "멀티시그널 (15분)", "is_public": True, "status": "testing"},
    {"value": "trend_follower_15m", "label": "추세추종 (15분)", "is_public": True, "status": "testing"},
    {"value": "signal_test_15m", "label": "매매 테스트 (15분)", "is_public": True, "status": "testing"},
]

# 백테스트 전용 별칭 (더 이상 사용하지 않지만 하위 호환용)
BACKTEST_STRATEGY_ALIASES: list[dict] = []
