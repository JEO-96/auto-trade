from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, time, timezone
from typing import Awaitable
from zoneinfo import ZoneInfo


from .config import ScalpingAlertConfig
from .formatter import format_signal_alert
from .limiter import AlertLimiter
from .providers import MarketDataProvider
from .signal_engine import SignalEngine

logger = logging.getLogger(__name__)

SendMessage = Callable[[str], None | Awaitable[None]]
KST = ZoneInfo("Asia/Seoul")


def _is_regular_session_open() -> bool:
    now = datetime.now(timezone.utc).astimezone(KST)
    return now.weekday() < 5 and time(9, 0) <= now.time() < time(15, 30)


class ScalpingAlertService:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        config: ScalpingAlertConfig,
        send_message: SendMessage,
        is_market_open: Callable[[], bool] | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.send_message = send_message
        self.is_market_open = is_market_open or _is_regular_session_open
        self.engine = SignalEngine(config)
        self.limiter = AlertLimiter(config)
        self._running = False
        self._last_scan: dict | None = None

    async def scan_once(self) -> dict:
        now = datetime.now(timezone.utc)
        if not self.is_market_open():
            result = {"evaluated": 0, "alerts": 0, "reason": "market closed"}
            self._last_scan = result
            return result

        snapshots = await self.provider.top_candidates(self.config.ranking_limit)
        alerts = 0
        rejected = 0
        for snapshot in snapshots:
            decision = self.engine.evaluate(snapshot)
            if not decision.should_alert:
                rejected += 1
                logger.info("[Scalping] rejected %s: %s", decision.symbol, ",".join(decision.rejections))
                continue

            allowed, reason = self.limiter.can_send(decision.symbol, now)
            if not allowed:
                rejected += 1
                logger.info("[Scalping] limited %s: %s", decision.symbol, reason)
                continue

            message = format_signal_alert(decision)
            alerts += 1
            self.limiter.record(decision.symbol, now)
            if self.config.dry_run:
                logger.info("[Scalping][dry-run] %s", message.replace("\n", " | "))
            else:
                maybe_awaitable = self.send_message(message)
                if asyncio.iscoroutine(maybe_awaitable):
                    await maybe_awaitable

        result = {"evaluated": len(snapshots), "alerts": alerts, "rejected": rejected}
        self._last_scan = result
        return result

    async def run(self) -> None:
        self._running = True
        try:
            while self._running:
                await self.scan_once()
                await asyncio.sleep(self.config.scan_tick_seconds)
        finally:
            await self.provider.close()

    def stop(self) -> None:
        self._running = False

    def status(self) -> dict:
        return {
            "running": self._running,
            "dry_run": self.config.dry_run,
            "last_scan": self._last_scan,
            "limiter": self.limiter.snapshot(datetime.now(timezone.utc)),
        }
