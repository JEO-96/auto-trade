from __future__ import annotations

from datetime import date, datetime, timedelta

from .config import ScalpingAlertConfig


class AlertLimiter:
    def __init__(self, config: ScalpingAlertConfig) -> None:
        self.config = config
        self._day: date | None = None
        self._daily_count = 0
        self._last_sent_at: dict[str, datetime] = {}

    def _reset_if_needed(self, now: datetime) -> None:
        current_day = now.date()
        if self._day != current_day:
            self._day = current_day
            self._daily_count = 0
            self._last_sent_at.clear()

    def can_send(self, symbol: str, now: datetime) -> tuple[bool, str | None]:
        self._reset_if_needed(now)
        if self._daily_count >= self.config.max_daily_alerts:
            return False, "daily alert limit reached"

        last = self._last_sent_at.get(symbol)
        if last is not None:
            cooldown = timedelta(minutes=self.config.cooldown_minutes)
            if now - last < cooldown:
                return False, "symbol cooldown active"

        return True, None

    def record(self, symbol: str, now: datetime) -> None:
        self._reset_if_needed(now)
        self._daily_count += 1
        self._last_sent_at[symbol] = now

    def snapshot(self, now: datetime) -> dict:
        self._reset_if_needed(now)
        return {
            "day": self._day.isoformat() if self._day else None,
            "daily_count": self._daily_count,
            "max_daily_alerts": self.config.max_daily_alerts,
            "tracked_symbols": sorted(self._last_sent_at.keys()),
        }
