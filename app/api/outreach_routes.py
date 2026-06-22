"""Outreach draft REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.outreach import (
    OutreachDraftListResponse,
    OutreachDraftResponse,
    OutreachDraftStatusUpdate,
    OutreachGenerateResponse,
)
from app.services.outreach_service import (
    archive_draft,
    generate_draft,
    get_draft,
    latest_draft_for_lead,
    list_drafts,
    mark_draft_reviewed,
    regenerate_draft,
    update_draft_status,
)

router = APIRouter(prefix="/api/outreach", tags=["outreach"])


@router.post("/leads/{lead_id}", response_model=OutreachGenerateResponse)
def api_generate_draft(lead_id: int, db: Session = Depends(get_db)) -> OutreachGenerateResponse:
    try:
        draft = generate_draft(db, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OutreachGenerateResponse(
        draft=OutreachDraftResponse.model_validate(draft),
        message="Draft created for review — not sent.",
    )


@router.post("/leads/{lead_id}/regenerate", response_model=OutreachGenerateResponse)
def api_regenerate_draft(lead_id: int, db: Session = Depends(get_db)) -> OutreachGenerateResponse:
    try:
        draft = regenerate_draft(db, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OutreachGenerateResponse(
        draft=OutreachDraftResponse.model_validate(draft),
        message="New draft created — previous drafts preserved.",
    )


@router.get("/leads/{lead_id}/latest", response_model=OutreachDraftResponse)
def api_latest_draft_for_lead(lead_id: int, db: Session = Depends(get_db)) -> OutreachDraftResponse:
    draft = latest_draft_for_lead(db, lead_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"No draft for lead {lead_id}")
    return OutreachDraftResponse.model_validate(draft)


@router.get("/drafts", response_model=OutreachDraftListResponse)
def api_list_drafts(
    db: Session = Depends(get_db),
    lead_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> OutreachDraftListResponse:
    items = list_drafts(db, lead_id=lead_id, status=status, limit=limit)
    return OutreachDraftListResponse(
        items=[OutreachDraftResponse.model_validate(d) for d in items],
        total=len(items),
    )


@router.get("/drafts/{draft_id}", response_model=OutreachDraftResponse)
def api_get_draft(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraftResponse:
    draft = get_draft(db, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
    return OutreachDraftResponse.model_validate(draft)


@router.patch("/drafts/{draft_id}/status", response_model=OutreachDraftResponse)
def api_update_draft_status(
    draft_id: int,
    body: OutreachDraftStatusUpdate,
    db: Session = Depends(get_db),
) -> OutreachDraftResponse:
    try:
        draft = update_draft_status(db, draft_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OutreachDraftResponse.model_validate(draft)


@router.post("/drafts/{draft_id}/reviewed", response_model=OutreachDraftResponse)
def api_mark_reviewed(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraftResponse:
    try:
        draft = mark_draft_reviewed(db, draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OutreachDraftResponse.model_validate(draft)


@router.post("/drafts/{draft_id}/archive", response_model=OutreachDraftResponse)
def api_archive_draft(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraftResponse:
    try:
        draft = archive_draft(db, draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return OutreachDraftResponse.model_validate(draft)
