from settings import settings

# ---------------------------------------------------------
# Exchange Configuration
# ---------------------------------------------------------
EXCHANGE_ID = 'upbit'  # Focus on Upbit for Korean market
API_KEY = settings.exchange_api_key
API_SECRET = settings.exchange_api_secret

# ---------------------------------------------------------
# Trading Parameters
# ---------------------------------------------------------
SYMBOL = 'BTC/KRW'     # Trading pair (KRW based)
TIMEFRAME = '1h'        # 1-Hour timeframe for James Momentum Breakout
LIMIT = 200             # Number of candles to fetch

# ---------------------------------------------------------
# Strategy Indicator Parameters
# ---------------------------------------------------------
RSI_PERIOD = 14
RSI_OVERBOUGHT = 60     # James Momentum Breakout upward cross threshold

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

VOLUME_MA_PERIOD = 20
VOLUME_SPIKE_MULTIPLIER = 2.0  # Volume must be > 200% of the MA

# ---------------------------------------------------------
# Risk Management Parameters
# ---------------------------------------------------------
RISK_PER_TRADE = 0.02    # Risk 2% of equity per trade
RISK_REWARD_RATIO = 1.5  # Target profit is 1.5x the risk (basic strategy)

# ---------------------------------------------------------
# Kakao OAuth Configuration
# ---------------------------------------------------------
KAKAO_REST_API_KEY = settings.kakao_rest_api_key
KAKAO_REDIRECT_URI = settings.kakao_redirect_uri

