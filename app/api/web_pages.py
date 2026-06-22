"""Dashboard GET routes."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.web_common import base_context, templates
from app.core.config import Settings, get_settings
from app.models.enums import LeadStatus, OutreachDraftStatus
from app.providers.registry import list_provider_summaries, list_providers
from app.services.dashboard_service import get_dashboard_data
from app.scheduler.service import list_scheduled_tasks
from app.services.export_service import filters_summary, get_export_job, list_export_jobs
from app.workers.queue import get_queue_stats
from app.services.inspection_service import get_inspection, list_inspections
from app.services.lead import (
    LeadFilters,
    get_lead,
    latest_inspection,
    latest_score,
    list_leads,
)
from app.services.scan import get_scan_job, list_scan_jobs
from app.services.scoring_service import get_priority_label_for_score, list_lead_scores
from app.services.outreach_service import list_drafts

router = APIRouter(tags=["dashboard"])


@dataclass
class InspectionFilters:
    reachable: str | None = None
    social_only: str | None = None
    branded_domain: str | None = None
    has_contact_page: str | None = None
    has_booking_flow: str | None = None
    ssl_present: str | None = None
    has_error: str | None = None


@router.get("/", response_class=HTMLResponse, name="dashboard_home")
def dashboard_home(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    ctx = base_context(request, settings)
    ctx.update(get_dashboard_data(db))
    ctx["queue_stats"] = get_queue_stats()
    ctx.update(
        {
            "active_nav": "home",
            "priority_label_for": get_priority_label_for_score,
        }
    )
    return templates.TemplateResponse(request, "dashboard/index.html", ctx)


@router.get("/scans", response_class=HTMLResponse, name="scans_list")
def scans_list(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    ctx = base_context(request, settings)
    ctx.update(
        {
            "scans": list_scan_jobs(db, limit=100),
            "providers": list_providers(),
            "provider_summaries": list_provider_summaries(),
            "active_nav": "scans",
        }
    )
    return templates.TemplateResponse(request, "dashboard/scans.html", ctx)


@router.get("/scans/{job_id}", response_class=HTMLResponse, name="scan_detail")
def scan_detail(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    job = get_scan_job(db, job_id)
    if job is None:
        ctx = base_context(request, settings)
        ctx["flash_error"] = f"Scan job {job_id} not found."
        return templates.TemplateResponse(request, "dashboard/scans.html", ctx, status_code=404)

    ctx = base_context(request, settings)
    ctx.update({"scan": job, "active_nav": "scans"})
    return templates.TemplateResponse(request, "dashboard/scan_detail.html", ctx)


@router.get("/leads", response_class=HTMLResponse, name="leads_list")
def leads_list(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    city: str | None = Query(None),
    state: str | None = Query(None),
    category: str | None = Query(None),
    source_name: str | None = Query(None),
    status: str | None = Query(None),
    has_website: str | None = Query(None),
    social_only: str | None = Query(None),
    min_score: int | None = Query(None),
    max_score: int | None = Query(None),
    inspected: str | None = Query(None),
    outreach_status: str | None = Query(None),
    search: str | None = Query(None),
    priority: str | None = Query(None),
    sort_by: str = Query("updated"),
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    filters = LeadFilters(
        city=city,
        state=state,
        category=category,
        source_name=source_name,
        status=status,
        has_website=has_website,
        social_only=social_only,
        min_score=min_score,
        max_score=max_score,
        inspected=inspected,
        outreach_status=outreach_status,
        search=search,
        priority=priority,
        sort_by=sort_by,
        page=page,
    )
    result = list_leads(db, filters)
    filter_params = {
        k: v
        for k, v in {
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
            "sort_by": sort_by,
        }.items()
        if v not in (None, "")
    }
    ctx = base_context(request, settings)
    ctx.update(
        {
            "result": result,
            "filters": filters,
            "filter_query": urlencode(filter_params),
            "lead_statuses": list(LeadStatus),
            "latest_score": latest_score,
            "latest_inspection": latest_inspection,
            "active_nav": "leads",
        }
    )
    return templates.TemplateResponse(request, "dashboard/leads.html", ctx)


@router.get("/leads/{lead_id}", response_class=HTMLResponse, name="lead_detail")
def lead_detail(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    lead = get_lead(db, lead_id)
    if lead is None:
        ctx = base_context(request, settings)
        ctx["flash_error"] = f"Lead {lead_id} not found."
        return templates.TemplateResponse(request, "dashboard/leads.html", ctx, status_code=404)

    ctx = base_context(request, settings)
    ctx.update(
        {
            "lead": lead,
            "inspection": latest_inspection(lead),
            "inspection_history": lead.inspections[:10],
            "score": latest_score(lead),
            "score_history": list_lead_scores(db, lead.id, limit=5),
            "latest_draft": lead.outreach_drafts[0] if lead.outreach_drafts else None,
            "draft_history": lead.outreach_drafts[:5],
            "priority_label": get_priority_label_for_score(latest_score(lead)),
            "queue_length": get_queue_stats()["total"],
            "active_nav": "leads",
        }
    )
    return templates.TemplateResponse(request, "dashboard/lead_detail.html", ctx)


@router.get("/exports", response_class=HTMLResponse, name="exports_list")
def exports_list(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    ctx = base_context(request, settings)
    ctx.update(
        {
            "exports": list_export_jobs(db),
            "lead_statuses": list(LeadStatus),
            "draft_statuses": [
                OutreachDraftStatus.DRAFT_READY,
                OutreachDraftStatus.REVIEWED,
                OutreachDraftStatus.ARCHIVED,
            ],
            "filters_summary": filters_summary,
            "active_nav": "exports",
        }
    )
    return templates.TemplateResponse(request, "dashboard/exports.html", ctx)


@router.get("/exports/download/{job_id}")
def export_download(
    job_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    from fastapi import HTTPException

    from app.utils.file_storage import ExportFileError, resolve_export_download_path

    job = get_export_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Export not ready (status: {job.status})")
    try:
        path = resolve_export_download_path(settings.export_dir, job)
    except ExportFileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path=path, filename=path.name, media_type="text/csv")


@router.get("/exports/{job_id}", response_class=HTMLResponse, name="export_detail")
def export_detail(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    job = get_export_job(db, job_id)
    if job is None:
        ctx = base_context(request, settings)
        ctx["flash_error"] = f"Export job {job_id} not found."
        return templates.TemplateResponse(request, "dashboard/exports.html", ctx, status_code=404)

    ctx = base_context(request, settings)
    ctx.update(
        {
            "export_job": job,
            "summary": filters_summary(job.filters),
            "active_nav": "exports",
        }
    )
    return templates.TemplateResponse(request, "exports/detail.html", ctx)


@router.get("/inspections", response_class=HTMLResponse, name="inspections_list")
def inspections_list(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    lead_id: int | None = Query(None),
    reachable: str | None = Query(None),
    social_only: str | None = Query(None),
    branded_domain: str | None = Query(None),
    has_contact_page: str | None = Query(None),
    has_booking_flow: str | None = Query(None),
    ssl_present: str | None = Query(None),
    has_error: str | None = Query(None),
) -> HTMLResponse:
    insp_filters = InspectionFilters(
        reachable=reachable,
        social_only=social_only,
        branded_domain=branded_domain,
        has_contact_page=has_contact_page,
        has_booking_flow=has_booking_flow,
        ssl_present=ssl_present,
        has_error=has_error,
    )
    ctx = base_context(request, settings)
    ctx.update(
        {
            "inspections": list_inspections(
                db,
                lead_id=lead_id,
                reachable=reachable,
                social_only=social_only,
                branded_domain=branded_domain,
                has_contact_page=has_contact_page,
                has_booking_flow=has_booking_flow,
                ssl_present=ssl_present,
                has_error=has_error,
                limit=100,
            ),
            "filter_lead_id": lead_id,
            "insp_filters": insp_filters,
            "queue_length": get_queue_stats()["total"],
            "active_nav": "inspections",
        }
    )
    return templates.TemplateResponse(request, "inspections/list.html", ctx)


@router.get("/inspections/{inspection_id}", response_class=HTMLResponse, name="inspection_detail")
def inspection_detail_page(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    inspection = get_inspection(db, inspection_id)
    if inspection is None:
        ctx = base_context(request, settings)
        ctx["flash_error"] = f"Inspection {inspection_id} not found."
        return templates.TemplateResponse(
            request, "inspections/list.html", ctx, status_code=404
        )

    ctx = base_context(request, settings)
    ctx.update(
        {
            "inspection": inspection,
            "lead": inspection.business_lead,
            "active_nav": "inspections",
        }
    )
    return templates.TemplateResponse(request, "inspections/detail.html", ctx)


@router.get("/schedules", response_class=HTMLResponse, name="schedules_list")
def schedules_list(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    from app.workers.job_types import ScheduledTaskType

    ctx = base_context(request, settings)
    ctx.update(
        {
            "schedules": list_scheduled_tasks(db),
            "task_types": list(ScheduledTaskType),
            "providers": list_providers(),
            "active_nav": "schedules",
        }
    )
    return templates.TemplateResponse(request, "dashboard/schedules.html", ctx)


@router.get("/settings", response_class=HTMLResponse, name="settings_page")
def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    ctx = base_context(request, settings)
    ctx.update(
        {
            "settings": settings,
            "providers": list_providers(),
            "queue_length": get_queue_stats()["total"],
            "queue_stats": get_queue_stats(),
            "active_nav": "settings",
        }
    )
    return templates.TemplateResponse(request, "dashboard/settings.html", ctx)


@router.get("/outreach", response_class=HTMLResponse, name="outreach_list")
def outreach_list(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    status: str | None = Query(None),
) -> HTMLResponse:
    ctx = base_context(request, settings)
    ctx.update(
        {
            "drafts": list_drafts(db, status=status, limit=100),
            "filter_status": status,
            "draft_statuses": [
                OutreachDraftStatus.DRAFT_READY,
                OutreachDraftStatus.REVIEWED,
                OutreachDraftStatus.ARCHIVED,
            ],
            "active_nav": "outreach",
        }
    )
    return templates.TemplateResponse(request, "outreach/list.html", ctx)


@router.get("/outreach/{draft_id}", response_class=HTMLResponse, name="outreach_detail")
def outreach_detail(
    draft_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    from app.services.outreach_service import get_draft

    draft = get_draft(db, draft_id)
    if draft is None:
        ctx = base_context(request, settings)
        ctx["flash_error"] = f"Draft {draft_id} not found."
        return templates.TemplateResponse(request, "outreach/list.html", ctx, status_code=404)

    ctx = base_context(request, settings)
    ctx.update(
        {
            "draft": draft,
            "lead": draft.business_lead,
            "active_nav": "outreach",
        }
    )
    return templates.TemplateResponse(request, "outreach/detail.html", ctx)
