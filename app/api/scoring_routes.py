"""REST API for lead scoring."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.scoring import BulkScoreResponse, LeadScoreResponse
from app.services.lead import get_lead
from app.services.scoring_rules import priority_label, priority_tier
from app.services.scoring_service import (
    get_lead_score,
    list_lead_scores,
    rescore_lead,
    rescore_leads_with_inspections,
    score_lead,
    score_unscored_leads,
)


def _score_to_response(score) -> LeadScoreResponse:
    data = LeadScoreResponse.model_validate(score)
    if score.breakdown:
        data.breakdown = score.breakdown
    else:
        data.breakdown = {
            "total_score": score.total_score,
            "priority_tier": priority_tier(score.total_score),
            "priority_label": priority_label(score.total_score),
            "factors": [],
            "sub_scores": {},
        }
    return data


router = APIRouter(prefix="/api/scoring", tags=["api-scoring"])


@router.post("/leads/{lead_id}", response_model=LeadScoreResponse)
def api_score_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadScoreResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        score = score_lead(db, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _score_to_response(score)


@router.post("/leads/{lead_id}/rescore", response_model=LeadScoreResponse)
def api_rescore_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadScoreResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        score = rescore_lead(db, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _score_to_response(score)


@router.get("/leads/{lead_id}", response_model=LeadScoreResponse)
def api_get_lead_score(lead_id: int, db: Session = Depends(get_db)) -> LeadScoreResponse:
    score = get_lead_score(db, lead_id)
    if score is None:
        raise HTTPException(status_code=404, detail="No score found for lead")
    return _score_to_response(score)


@router.get("/leads/{lead_id}/history", response_model=list[LeadScoreResponse])
def api_lead_score_history(
    lead_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> list[LeadScoreResponse]:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return [_score_to_response(s) for s in list_lead_scores(db, lead_id, limit=limit)]


@router.post("/bulk/unscored", response_model=BulkScoreResponse)
def api_score_unscored(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
) -> BulkScoreResponse:
    result = score_unscored_leads(db, limit=limit)
    return BulkScoreResponse(**result)


@router.post("/bulk/rescore-inspected", response_model=BulkScoreResponse)
def api_rescore_inspected(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
) -> BulkScoreResponse:
    result = rescore_leads_with_inspections(db, limit=limit)
    return BulkScoreResponse(
        scored=result.get("rescored"),
        rescored=result.get("rescored"),
        errors=result["errors"],
        attempted=result["attempted"],
    )
