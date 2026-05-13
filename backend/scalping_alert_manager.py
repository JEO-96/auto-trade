from __future__ import annotations

import asyncio
import logging

from core.scalping.config import ScalpingAlertConfig
from core.scalping.providers import FixtureMarketDataProvider, KisRestMarketDataProvider
from core.scalping.service import ScalpingAlertService
from notifications import send_stock_alert_broadcast
from settings import settings

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None
_service: ScalpingAlertService | None = None


async def _send_alert(message: str) -> None:
    await send_stock_alert_broadcast(message)


def _build_service() -> ScalpingAlertService:
    from core.scalping.kis_client import KisRestClient

    config = ScalpingAlertConfig(dry_run=settings.scalping_alert_dry_run)
    if settings.kis_app_key and settings.kis_app_secret and settings.kis_access_token:
        client = KisRestClient(
            app_key=settings.kis_app_key,
            app_secret=settings.kis_app_secret,
            access_token=settings.kis_access_token,
        )
        provider = KisRestMarketDataProvider(client)
    else:
        provider = FixtureMarketDataProvider([])
    return ScalpingAlertService(provider=provider, config=config, send_message=_send_alert)


async def start() -> dict:
    global _task, _service
    if _task is not None and not _task.done():
        return status()
    _service = _build_service()
    _task = asyncio.create_task(_service.run())
    logger.info("[Scalping] alert service started")
    return status()


async def stop() -> dict:
    global _task, _service
    if _service is not None:
        _service.stop()
    if _task is not None and not _task.done():
        await asyncio.wait([_task], timeout=5)
    logger.info("[Scalping] alert service stopped")
    return status()


def status() -> dict:
    running = _task is not None and not _task.done()
    return {
        "running": running,
        "configured": bool(settings.kis_app_key and settings.kis_app_secret and settings.kis_access_token),
        "service": _service.status() if _service is not None else None,
    }
