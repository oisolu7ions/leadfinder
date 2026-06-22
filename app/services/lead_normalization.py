"""Convert provider records into normalized internal lead data."""

from __future__ import annotations

from dataclasses import dataclass

from app.providers.base import ProviderRecord
from app.utils.normalize import (
    address_dedup_key,
    extract_domain,
    normalize_business_name,
    normalize_city,
    normalize_phone,
    normalize_state,
    normalize_website_url,
    partition_website_and_social,
)


@dataclass(frozen=True)
class NormalizedLeadData:
    """Internal normalized lead fields ready for persistence."""

    source_name: str
    business_name: str
    normalized_name: str
    category: str | None
    phone: str | None
    email: str | None
    address_line1: str | None
    normalized_address_key: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    website_url: str | None
    normalized_domain: str | None
    social_links: dict | None
    source_url: str | None
    external_id: str | None
    raw_payload: dict | None


def normalize_provider_record(record: ProviderRecord, source_name: str) -> NormalizedLeadData:
    """Map a provider record into the internal normalized lead structure."""
    website_url, social_links = partition_website_and_social(
        record.website_url,
        record.social_links,
    )
    phone_digits = normalize_phone(record.phone)

    return NormalizedLeadData(
        source_name=source_name,
        business_name=record.business_name.strip(),
        normalized_name=normalize_business_name(record.business_name),
        category=record.category.strip() if record.category else None,
        phone=phone_digits or record.phone,
        email=record.email,
        address_line1=record.address_line1.strip() if record.address_line1 else None,
        normalized_address_key=address_dedup_key(
            record.address_line1,
            record.city,
            record.state,
            record.postal_code,
        ),
        city=normalize_city(record.city),
        state=normalize_state(record.state),
        postal_code=record.postal_code.strip() if record.postal_code else None,
        country=record.country,
        website_url=website_url,
        normalized_domain=extract_domain(website_url),
        social_links=social_links,
        source_url=record.source_url,
        external_id=record.external_id,
        raw_payload=record.raw_payload,
    )
