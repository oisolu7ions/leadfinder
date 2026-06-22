"""Dashboard POST action routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.api.deps import get_db
from app.api.web_common import redirect_with_message
from app.core.config import Settings, get_settings
from app.scheduler.service import create_scheduled_task, update_scheduled_task
from app.services.export_service import create_export_job, normalize_export_filters, run_export_job
from app.services.inspection_service import inspect_lead
from app.services.lead import list_uninspected_lead_ids
from app.services.outreach_service import generate_draft, mark_draft_reviewed, regenerate_draft
from app.services.scan import create_scan_job, run_scan_job
from app.services.scoring_service import (
    rescore_lead,
    score_lead,
    score_unscored_leads,
)
from app.utils.csrf import validate_csrf_token
from app.workers.enqueue import (
    create_and_enqueue_export,
    create_and_enqueue_scan,
    enqueue_bulk_inspection,
    enqueue_inspection,
    enqueue_inspections,
    enqueue_outreach,
    enqueue_score,
    enqueue_score_bulk,
)
from app.workers.queue import get_queue_length
from app.workers.job_types import ScheduledTaskType

router = APIRouter(tags=["dashboard-actions"])


def _require_csrf(settings: Settings, csrf_token: str | None) -> None:
    if not validate_csrf_token(settings.secret_key, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")


@router.post("/scans/run", name="run_scan")
def run_scan_action(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    csrf_token: str = Form(...),
    category: str = Form(...),
    city: str = Form(...),
    state: str = Form(""),
    source_name: str = Form("mock"),
    limit: int = Form(50),
    mode: str = Form("queue"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    if mode == "queue":
        job_id, qlen = create_and_enqueue_scan(
            db, category, city, source_name, state or None, limit=limit
        )
        return redirect_with_message(
            "/scans",
            message=f"Scan #{job_id} queued (queue length: {qlen}). Start a worker to process it.",
        )
    job = create_scan_job(db, category, city, source_name, state or None)
    db.commit()
    try:
        run_scan_job(db, job.id, limit=limit)
        return redirect_with_message("/scans", message=f"Scan #{job.id} completed successfully.")
    except Exception as exc:
        return redirect_with_message("/scans", error=f"Scan #{job.id} failed: {exc}")


@router.post("/leads/{lead_id}/inspect", name="inspect_lead")
def inspect_lead_action(
    lead_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    try:
        inspect_lead(db, lead_id)
        return redirect_with_message(f"/leads/{lead_id}", message="Inspection completed.")
    except Exception as exc:
        return redirect_with_message(f"/leads/{lead_id}", error=str(exc))


@router.post("/leads/{lead_id}/queue-inspection", name="queue_inspect_lead")
def queue_inspect_lead_action(
    lead_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    enqueue_inspection(lead_id)
    qlen = get_queue_length()
    return redirect_with_message(
        f"/leads/{lead_id}",
        message=f"Inspection queued (queue length: {qlen}).",
    )


@router.post("/leads/inspect-uninspected", name="inspect_uninspected")
def inspect_uninspected_action(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    limit: int = Form(25),
    mode: str = Form("queue"),
    next: str = Form("/leads"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    if mode == "queue":
        qlen = enqueue_bulk_inspection(db, uninspected_limit=limit)
        return redirect_with_message(
            next,
            message=f"Queued up to {limit} uninspected lead(s) (queue length: {qlen}).",
        )
    lead_ids = list_uninspected_lead_ids(db, limit=limit)
    count = 0
    errors = 0
    for lead_id in lead_ids:
        try:
            inspect_lead(db, lead_id)
            count += 1
        except Exception:
            errors += 1
            db.rollback()
    msg = f"Inspected {count} lead(s)."
    if errors:
        msg += f" {errors} failed."
    return redirect_with_message(next, message=msg)


@router.post("/leads/{lead_id}/score", name="score_lead")
def score_lead_action(
    lead_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    mode: str = Form("sync"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    if mode == "queue":
        qlen = enqueue_score(lead_id)
        return redirect_with_message(
            f"/leads/{lead_id}",
            message=f"Scoring queued (queue length: {qlen}).",
        )
    try:
        score_lead(db, lead_id)
        return redirect_with_message(f"/leads/{lead_id}", message="Lead scored.")
    except Exception as exc:
        return redirect_with_message(f"/leads/{lead_id}", error=str(exc))


@router.post("/leads/{lead_id}/rescore", name="rescore_lead")
def rescore_lead_action(
    lead_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    try:
        rescore_lead(db, lead_id)
        return redirect_with_message(f"/leads/{lead_id}", message="Lead rescored.")
    except Exception as exc:
        return redirect_with_message(f"/leads/{lead_id}", error=str(exc))


@router.post("/leads/score-unscored", name="score_unscored_leads")
def score_unscored_action(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    limit: int = Form(50),
    mode: str = Form("sync"),
    next: str = Form("/leads"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    if mode == "queue":
        qlen = enqueue_score_bulk(limit=limit)
        return redirect_with_message(
            next,
            message=f"Bulk scoring queued for up to {limit} lead(s) (queue length: {qlen}).",
        )
    result = score_unscored_leads(db, limit=limit)
    return redirect_with_message(
        next,
        message=f"Scored {result['scored']} lead(s). {result['errors']} error(s).",
    )


@router.post("/leads/{lead_id}/outreach", name="generate_outreach")
def generate_outreach_action(
    lead_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    mode: str = Form("sync"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    if mode == "queue":
        qlen = enqueue_outreach(lead_id)
        return redirect_with_message(
            f"/leads/{lead_id}",
            message=f"Outreach draft generation queued (queue length: {qlen}).",
        )
    try:
        generate_draft(db, lead_id)
        return redirect_with_message(f"/leads/{lead_id}", message="Outreach draft generated (review only).")
    except Exception as exc:
        return redirect_with_message(f"/leads/{lead_id}", error=str(exc))


@router.post("/leads/{lead_id}/outreach/regenerate", name="regenerate_outreach")
def regenerate_outreach_action(
    lead_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    try:
        regenerate_draft(db, lead_id)
        return redirect_with_message(
            f"/leads/{lead_id}",
            message="New outreach draft generated — previous drafts preserved.",
        )
    except Exception as exc:
        return redirect_with_message(f"/leads/{lead_id}", error=str(exc))


@router.post("/outreach/drafts/{draft_id}/reviewed", name="mark_draft_reviewed")
def mark_draft_reviewed_action(
    draft_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    next: str = Form("/outreach"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    try:
        draft = mark_draft_reviewed(db, draft_id)
        return redirect_with_message(next or f"/leads/{draft.business_lead_id}", message="Draft marked reviewed.")
    except Exception as exc:
        return redirect_with_message(next, error=str(exc))


@router.post("/exports/run", name="run_export")
def run_export_action(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    city: str = Form(""),
    state: str = Form(""),
    category: str = Form(""),
    source_name: str = Form(""),
    status: str = Form(""),
    has_website: str = Form(""),
    social_only: str = Form(""),
    min_score: str = Form(""),
    max_score: str = Form(""),
    inspected: str = Form(""),
    outreach_status: str = Form(""),
    search: str = Form(""),
    priority: str = Form(""),
    insp_reachable: str = Form(""),
    insp_blank_website: str = Form(""),
    insp_social_only: str = Form(""),
    insp_has_contact_page: str = Form(""),
    insp_has_booking_flow: str = Form(""),
    format: str = Form("csv"),
    mode: str = Form("queue"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    filters = normalize_export_filters(
        {
            "city": city,
            "state": state,
            "category": category,
            "source_name": source_name,
            "status": status,
            "has_website": has_website,
            "social_only": social_only,
            "min_score": min_score,
            "max_score": max_score,
            "inspected": inspected,
            "outreach_status": outreach_status,
            "search": search,
            "priority": priority,
            "insp_reachable": insp_reachable,
            "insp_blank_website": insp_blank_website,
            "insp_social_only": insp_social_only,
            "insp_has_contact_page": insp_has_contact_page,
            "insp_has_booking_flow": insp_has_booking_flow,
        }
    )
    if mode == "queue":
        job_id, qlen = create_and_enqueue_export(db, filters, fmt=format)
        return redirect_with_message(
            f"/exports/{job_id}",
            message=f"Export #{job_id} queued (queue length: {qlen}). Refresh when complete.",
        )
    job = create_export_job(db, filters, fmt=format)
    db.commit()
    try:
        job = run_export_job(db, job.id)
        return redirect_with_message(
            f"/exports/{job.id}",
            message=f"Export #{job.id} ready — {job.row_count} row(s).",
        )
    except Exception as exc:
        return redirect_with_message("/exports", error=f"Export failed: {exc}")


@router.post("/leads/export", name="export_leads_view")
def export_leads_view_action(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    city: str = Form(""),
    state: str = Form(""),
    category: str = Form(""),
    source_name: str = Form(""),
    status: str = Form(""),
    has_website: str = Form(""),
    social_only: str = Form(""),
    min_score: str = Form(""),
    max_score: str = Form(""),
    inspected: str = Form(""),
    outreach_status: str = Form(""),
    search: str = Form(""),
    priority: str = Form(""),
    sort_by: str = Form("updated"),
    mode: str = Form("queue"),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    filters = normalize_export_filters(
        {
            "city": city,
            "state": state,
            "category": category,
            "source_name": source_name,
            "status": status,
            "has_website": has_website,
            "social_only": social_only,
            "min_score": min_score,
            "max_score": max_score,
            "inspected": inspected,
            "outreach_status": outreach_status,
            "search": search,
            "priority": priority,
        }
    )
    if mode == "queue":
        job_id, qlen = create_and_enqueue_export(db, filters)
        return redirect_with_message(
            f"/exports/{job_id}",
            message=f"Export #{job_id} queued from current view (queue length: {qlen}).",
        )
    job = create_export_job(db, filters)
    db.commit()
    try:
        job = run_export_job(db, job.id)
        return redirect_with_message(
            f"/exports/{job.id}",
            message=f"Exported {job.row_count} lead(s) from current view.",
        )
    except Exception as exc:
        return redirect_with_message("/leads", error=f"Export failed: {exc}")


@router.post("/schedules/create", name="create_schedule")
def create_schedule_action(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    name: str = Form(...),
    task_type: str = Form(...),
    interval_minutes: int = Form(60),
    category: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    source_name: str = Form("mock"),
    limit: int = Form(50),
    uninspected_limit: int = Form(25),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    payload: dict = {}
    if task_type == ScheduledTaskType.SCAN.value:
        if not category or not city:
            return redirect_with_message("/schedules", error="Scan schedules require category and city.")
        payload = {
            "category": category,
            "city": city,
            "state": state or None,
            "source_name": source_name,
            "limit": limit,
        }
    elif task_type == ScheduledTaskType.INSPECT_UNREVIEWED.value:
        payload = {"uninspected_limit": uninspected_limit, "auto_score": True}
    elif task_type == ScheduledTaskType.SCORE_UNSCORED.value:
        payload = {"limit": limit}
    elif task_type == ScheduledTaskType.EXPORT.value:
        payload = {"filters": {}}
    else:
        return redirect_with_message("/schedules", error=f"Unknown task type: {task_type}")

    try:
        task = create_scheduled_task(
            db,
            name=name,
            task_type=task_type,
            interval_minutes=interval_minutes,
            payload=payload,
        )
    except Exception as exc:
        return redirect_with_message("/schedules", error=str(exc))
    return redirect_with_message("/schedules", message=f"Schedule #{task.id} created.")


@router.post("/schedules/{task_id}/toggle", name="toggle_schedule")
def toggle_schedule_action(
    task_id: int,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    enabled: str = Form(...),
) -> RedirectResponse:
    _require_csrf(settings, csrf_token)
    try:
        update_scheduled_task(db, task_id, enabled=enabled.lower() == "true")
    except ValueError as exc:
        return redirect_with_message("/schedules", error=str(exc))
    state = "enabled" if enabled.lower() == "true" else "disabled"
    return redirect_with_message("/schedules", message=f"Schedule #{task_id} {state}.")
