from __future__ import annotations

from fastapi import APIRouter, Depends

import models
import scalping_alert_manager
from dependencies import get_admin_user

router = APIRouter(prefix="/admin/scalping-alerts", tags=["admin-scalping-alerts"])


@router.get("/status")
def get_scalping_alert_status(admin: models.User = Depends(get_admin_user)):
    return scalping_alert_manager.status()


@router.post("/start")
async def start_scalping_alerts(admin: models.User = Depends(get_admin_user)):
    return await scalping_alert_manager.start()


@router.post("/stop")
async def stop_scalping_alerts(admin: models.User = Depends(get_admin_user)):
    return await scalping_alert_manager.stop()
