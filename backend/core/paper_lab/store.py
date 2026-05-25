from __future__ import annotations

import json

import models


class SqlAlchemyPaperLabStore:
    def __init__(self, db_factory):
        self.db_factory = db_factory

    def load_state(self, run_id: str) -> dict | None:
        with self.db_factory() as db:
            row = (
                db.query(models.PaperLabRunState)
                .filter(models.PaperLabRunState.run_id == run_id)
                .first()
            )
            return json.loads(row.state_json) if row else None

    def save_state(self, run_id: str, state: dict) -> None:
        with self.db_factory() as db:
            row = (
                db.query(models.PaperLabRunState)
                .filter(models.PaperLabRunState.run_id == run_id)
                .first()
            )
            payload = json.dumps(state, ensure_ascii=False)
            if row is None:
                row = models.PaperLabRunState(run_id=run_id, state_json=payload)
                db.add(row)
            else:
                row.state_json = payload
            db.commit()

    def save_snapshot(self, run_id: str, snapshot: dict) -> None:
        with self.db_factory() as db:
            db.add(
                models.PaperLabDailySnapshot(
                    run_id=run_id,
                    window_start=snapshot["window_start"],
                    window_end=snapshot["window_end"],
                    total_equity=float(snapshot["summary"]["total_equity"]),
                    realized_pnl=float(snapshot["summary"]["realized_pnl"]),
                    unrealized_pnl=float(snapshot["summary"]["unrealized_pnl"]),
                    snapshot_json=json.dumps(snapshot, ensure_ascii=False),
                )
            )
            db.commit()
