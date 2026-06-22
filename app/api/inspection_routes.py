"""REST API for website inspections."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.inspection import (
    InspectionListResponse,
    InspectionQueueRequest,
    InspectionQueueResponse,
    InspectionResponse,
    InspectionRunRequest,
)
from app.services.inspection_queue import enqueue_inspection, enqueue_inspections, get_queue_length
from app.services.inspection_service import (
    count_inspections,
    get_inspection,
    inspect_lead,
    list_inspections,
)
from app.services.lead import get_lead, list_uninspected_lead_ids

router = APIRouter(prefix="/api/inspections", tags=["api-inspections"])


@router.post("/leads/{lead_id}", response_model=InspectionResponse)
def api_inspect_lead_now(
    lead_id: int,
    body: InspectionRunRequest | None = None,
    db: Session = Depends(get_db),
) -> InspectionResponse:
    """Run inspection synchronously for one lead."""
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    body = body or InspectionRunRequest()
    try:
        inspection = inspect_lead(
            db,
            lead_id,
            run_browser=body.run_browser,
            auto_score=body.auto_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return InspectionResponse.model_validate(inspection)


@router.post("/leads/{lead_id}/queue", response_model=InspectionQueueResponse)
def api_queue_lead_inspection(lead_id: int, db: Session = Depends(get_db)) -> InspectionQueueResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    length = enqueue_inspection(lead_id)
    return InspectionQueueResponse(queued=1, queue_length=length)


@router.post("/queue", response_model=InspectionQueueResponse)
def api_queue_inspections(
    body: InspectionQueueRequest,
    db: Session = Depends(get_db),
) -> InspectionQueueResponse:
    """Queue one or more leads, or batch-queue uninspected leads."""
    lead_ids: list[int] = list(body.lead_ids or [])
    if body.uninspected_limit:
        lead_ids.extend(list_uninspected_lead_ids(db, limit=body.uninspected_limit))
    lead_ids = list(dict.fromkeys(lead_ids))
    if not lead_ids:
        return InspectionQueueResponse(queued=0, queue_length=get_queue_length())
    length = enqueue_inspections(lead_ids)
    return InspectionQueueResponse(queued=len(lead_ids), queue_length=length)


@router.get("/leads/{lead_id}/history", response_model=InspectionListResponse)
def api_lead_inspection_history(
    lead_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> InspectionListResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    items = list_inspections(db, lead_id=lead_id, limit=limit)
    total = count_inspections(db, lead_id=lead_id)
    return InspectionListResponse(
        items=[InspectionResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("", response_model=InspectionListResponse)
def api_list_inspections(
    db: Session = Depends(get_db),
    lead_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> InspectionListResponse:
    items = list_inspections(db, lead_id=lead_id, limit=limit, offset=offset)
    total = count_inspections(db, lead_id=lead_id)
    return InspectionListResponse(
        items=[InspectionResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{inspection_id}", response_model=InspectionResponse)
def api_get_inspection(inspection_id: int, db: Session = Depends(get_db)) -> InspectionResponse:
    inspection = get_inspection(db, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return InspectionResponse.model_validate(inspection)
