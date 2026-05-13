from datetime import datetime, timedelta, timezone

from core.scalping.config import ScalpingAlertConfig
from core.scalping.limiter import AlertLimiter


def test_limiter_allows_then_blocks_symbol_cooldown():
    limiter = AlertLimiter(ScalpingAlertConfig(cooldown_minutes=45))
    now = datetime(2026, 5, 13, 9, 30, tzinfo=timezone.utc)

    allowed, reason = limiter.can_send("005930", now)
    assert allowed is True
    assert reason is None

    limiter.record("005930", now)

    allowed, reason = limiter.can_send("005930", now + timedelta(minutes=10))
    assert allowed is False
    assert reason == "symbol cooldown active"


def test_limiter_resets_daily_count_on_new_day():
    limiter = AlertLimiter(ScalpingAlertConfig(max_daily_alerts=1, cooldown_minutes=0))
    day1 = datetime(2026, 5, 13, 9, 30, tzinfo=timezone.utc)
    day2 = datetime(2026, 5, 14, 9, 30, tzinfo=timezone.utc)

    limiter.record("005930", day1)
    allowed, reason = limiter.can_send("000660", day1)
    assert allowed is False
    assert reason == "daily alert limit reached"

    allowed, reason = limiter.can_send("000660", day2)
    assert allowed is True
    assert reason is None
