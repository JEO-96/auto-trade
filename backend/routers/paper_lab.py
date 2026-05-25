from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from core.paper_lab.runtime import DEFAULT_RUN_ID
from dependencies import get_admin_user, get_db
from settings import settings

router = APIRouter(prefix="/admin/paper-lab", tags=["admin-paper-lab"])


@router.get("/status")
def get_paper_lab_status(
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    state_row = (
        db.query(models.PaperLabRunState)
        .filter(models.PaperLabRunState.run_id == DEFAULT_RUN_ID)
        .first()
    )
    snapshots = (
        db.query(models.PaperLabDailySnapshot)
        .filter(models.PaperLabDailySnapshot.run_id == DEFAULT_RUN_ID)
        .order_by(models.PaperLabDailySnapshot.created_at.desc())
        .limit(7)
        .all()
    )
    return {
        "enabled": settings.paper_lab_enabled,
        "run_id": DEFAULT_RUN_ID,
        "state": json.loads(state_row.state_json) if state_row else None,
        "snapshots": [json.loads(row.snapshot_json) for row in snapshots],
    }
