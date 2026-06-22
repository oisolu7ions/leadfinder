"""Job handlers — workers call existing services only."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.export_service import run_export_job
from app.services.inspection_service import inspect_lead
from app.services.lead import list_uninspected_lead_ids
from app.services.outreach_service import generate_draft
from app.services.scan import run_scan_job
from app.services.scoring_service import score_lead, score_unscored_leads
from app.workers.job_types import JobType
from app.workers.queue import JobEnvelope

logger = get_logger(__name__)


def handle_job(db: Session, envelope: JobEnvelope) -> None:
    """Dispatch a job envelope to the appropriate service handler."""
    handlers = {
        JobType.SCAN.value: _handle_scan,
        JobType.INSPECT.value: _handle_inspect,
        JobType.INSPECT_BULK.value: _handle_inspect_bulk,
        JobType.SCORE.value: _handle_score,
        JobType.SCORE_BULK.value: _handle_score_bulk,
        JobType.OUTREACH.value: _handle_outreach,
        JobType.EXPORT.value: _handle_export,
    }
    handler = handlers.get(envelope.type)
    if handler is None:
        raise ValueError(f"Unknown job type: {envelope.type}")
    handler(db, envelope.payload)


def _handle_scan(db: Session, payload: dict) -> None:
    run_scan_job(db, int(payload["scan_job_id"]), limit=int(payload.get("limit", 50)))


def _handle_inspect(db: Session, payload: dict) -> None:
    inspect_lead(
        db,
        int(payload["lead_id"]),
        run_browser=payload.get("run_browser"),
        auto_score=bool(payload.get("auto_score", True)),
    )


def _handle_inspect_bulk(db: Session, payload: dict) -> None:
    lead_ids = list(payload.get("lead_ids") or [])
    if payload.get("uninspected_limit"):
        lead_ids.extend(
            list_uninspected_lead_ids(db, limit=int(payload["uninspected_limit"]))
        )
    lead_ids = list(dict.fromkeys(int(i) for i in lead_ids))
    errors = 0
    for lead_id in lead_ids:
        try:
            inspect_lead(db, lead_id, auto_score=bool(payload.get("auto_score", True)))
        except Exception:
            errors += 1
            db.rollback()
            logger.exception("inspect_bulk_item_failed", lead_id=lead_id)
    if errors and errors == len(lead_ids):
        raise RuntimeError(f"All {errors} bulk inspection(s) failed")


def _handle_score(db: Session, payload: dict) -> None:
    score_lead(db, int(payload["lead_id"]))


def _handle_score_bulk(db: Session, payload: dict) -> None:
    result = score_unscored_leads(db, limit=int(payload.get("limit", 50)))
    logger.info("score_bulk_completed", **result)
    if result.get("errors", 0) and result.get("scored", 0) == 0:
        raise RuntimeError(f"Bulk scoring failed: {result}")


def _handle_outreach(db: Session, payload: dict) -> None:
    generate_draft(db, int(payload["lead_id"]))


def _handle_export(db: Session, payload: dict) -> None:
    run_export_job(db, int(payload["export_job_id"]))
