"""Lead persistence — deduplication and database upserts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_lead import BusinessLead
from app.providers.base import ProviderRecord
from app.services.lead_normalization import NormalizedLeadData, normalize_provider_record


def find_existing_lead(
    db: Session,
    normalized: NormalizedLeadData,
) -> BusinessLead | None:
    """Find an existing lead using dedup keys (ordered by reliability)."""
    if normalized.external_id:
        existing = db.scalar(
            select(BusinessLead).where(
                BusinessLead.source_name == normalized.source_name,
                BusinessLead.external_id == normalized.external_id,
            )
        )
        if existing:
            return existing

    if normalized.phone:
        existing = db.scalar(
            select(BusinessLead).where(BusinessLead.phone == normalized.phone)
        )
        if existing:
            return existing

    if normalized.normalized_domain:
        existing = db.scalar(
            select(BusinessLead).where(
                BusinessLead.normalized_domain == normalized.normalized_domain
            )
        )
        if existing:
            return existing

    if normalized.normalized_address_key:
        existing = db.scalar(
            select(BusinessLead).where(
                BusinessLead.normalized_address_key == normalized.normalized_address_key
            )
        )
        if existing:
            return existing

    if normalized.normalized_name and normalized.city:
        existing = db.scalar(
            select(BusinessLead).where(
                BusinessLead.normalized_name == normalized.normalized_name,
                BusinessLead.city == normalized.city,
            )
        )
        if existing:
            return existing

    return None


def upsert_lead(
    db: Session,
    record: ProviderRecord,
    source_name: str,
    scan_job_id: int | None = None,
) -> tuple[BusinessLead, bool]:
    """Insert or update a lead. Returns (lead, inserted)."""
    normalized = normalize_provider_record(record, source_name)
    existing = find_existing_lead(db, normalized)

    payload = {
        "business_name": normalized.business_name,
        "normalized_name": normalized.normalized_name,
        "category": normalized.category,
        "phone": normalized.phone,
        "email": normalized.email,
        "address_line1": normalized.address_line1,
        "normalized_address_key": normalized.normalized_address_key,
        "city": normalized.city,
        "state": normalized.state,
        "postal_code": normalized.postal_code,
        "country": normalized.country,
        "website_url": normalized.website_url,
        "normalized_domain": normalized.normalized_domain,
        "social_links": normalized.social_links,
        "source_url": normalized.source_url,
        "raw_payload": normalized.raw_payload,
        "scan_job_id": scan_job_id,
    }

    if existing:
        for key, value in payload.items():
            if value is not None:
                setattr(existing, key, value)
        if not existing.external_id and normalized.external_id:
            existing.external_id = normalized.external_id
        db.flush()
        return existing, False

    lead = BusinessLead(
        source_name=source_name,
        external_id=normalized.external_id,
        **payload,
    )
    db.add(lead)
    db.flush()
    return lead, True
