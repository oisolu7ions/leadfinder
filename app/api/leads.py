"""REST API for business leads."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.lead import LeadListResponse, LeadResponse
from app.services.lead import LeadFilters, get_lead, list_leads

router = APIRouter(prefix="/api/leads", tags=["api-leads"])


@router.get("", response_model=LeadListResponse)
def api_list_leads(
    db: Session = Depends(get_db),
    city: str | None = Query(None),
    state: str | None = Query(None),
    category: str | None = Query(None),
    status: str | None = Query(None),
    has_website: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
) -> LeadListResponse:
    result = list_leads(
        db,
        LeadFilters(
            city=city,
            state=state,
            category=category,
            status=status,
            has_website=has_website,
            search=search,
            page=page,
            per_page=per_page,
        ),
    )
    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in result.leads],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def api_get_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadResponse:
    lead = get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)
