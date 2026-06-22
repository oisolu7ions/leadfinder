"""Map TomTom Search API payloads to internal ProviderRecord objects."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderRecord


def _street_line(address: dict[str, Any]) -> str | None:
    number = (address.get("streetNumber") or "").strip()
    name = (address.get("streetName") or "").strip()
    parts = [p for p in (number, name) if p]
    if parts:
        return " ".join(parts)
    freeform = (address.get("freeformAddress") or "").strip()
    return freeform or None


def _primary_category(poi: dict[str, Any], fallback: str) -> str:
    categories = poi.get("categories") or []
    if categories:
        first = categories[0]
        if isinstance(first, str) and first.strip():
            return first.replace("_", " ").strip()
        if isinstance(first, dict) and first.get("name"):
            return str(first["name"])
    return fallback


def tomtom_result_to_record(
    result: dict[str, Any],
    *,
    requested_category: str,
    requested_city: str,
    requested_state: str | None,
) -> ProviderRecord | None:
    """Convert one TomTom search result into a ProviderRecord."""
    poi = result.get("poi") or {}
    address = result.get("address") or {}
    name = poi.get("name")
    if not name:
        return None

    external_id = str(result.get("id") or poi.get("id") or "")
    if not external_id:
        return None

    municipality = (address.get("municipality") or requested_city or "").strip()
    state = (address.get("countrySubdivision") or requested_state or "").strip() or None
    website = (poi.get("url") or "").strip() or None

    return ProviderRecord(
        business_name=str(name),
        category=_primary_category(poi, requested_category),
        city=municipality,
        state=state,
        external_id=external_id,
        phone=(poi.get("phone") or "").strip() or None,
        email=None,
        address_line1=_street_line(address),
        postal_code=(address.get("postalCode") or "").strip() or None,
        country=(address.get("countryCode") or "US").strip() or "US",
        website_url=website,
        social_links=None,
        source_url=website,
        raw_payload={
            "provider": "tomtom",
            "tomtom_id": external_id,
            "poi": poi,
            "address": address,
            "position": result.get("position"),
            "search_context": {
                "requested_category": requested_category,
                "requested_city": requested_city,
                "requested_state": requested_state,
            },
            "tomtom_search_hit": result,
        },
    )


def parse_tomtom_search_response(
    payload: dict[str, Any],
    *,
    requested_category: str,
    requested_city: str,
    requested_state: str | None,
) -> list[ProviderRecord]:
    """Parse TomTom /search JSON body."""
    records: list[ProviderRecord] = []
    for result in payload.get("results") or []:
        if (result.get("type") or "").upper() != "POI" and not result.get("poi"):
            continue
        record = tomtom_result_to_record(
            result,
            requested_category=requested_category,
            requested_city=requested_city,
            requested_state=requested_state,
        )
        if record:
            records.append(record)
    return records


def extract_geocode_position(payload: dict[str, Any]) -> tuple[float, float]:
    """Return lat/lon from a geocode response."""
    results = payload.get("results") or []
    if not results:
        raise ValueError("TomTom geocode returned no results for the requested location")
    position = results[0].get("position") or {}
    lat = position.get("lat")
    lon = position.get("lon")
    if lat is None or lon is None:
        raise ValueError("TomTom geocode result missing coordinates")
    return float(lat), float(lon)
