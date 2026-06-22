"""TomTom Search API live business search provider."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.providers.base import BaseProvider, ProviderSearchResult
from app.providers.errors import ProviderAPIError, ProviderNotConfiguredError
from app.providers.tomtom_client import TomTomClient
from app.providers.tomtom_parser import (
    extract_geocode_position,
    parse_tomtom_search_response,
)

logger = get_logger(__name__)


class TomTomProvider(BaseProvider):
    """Live local business search via TomTom Search API."""

    name = "tomtom"
    display_name = "TomTom Search (Live)"
    is_live = True
    default_scan_limit = 15
    max_scan_limit = 50

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.tomtom_api_key:
            raise ProviderNotConfiguredError(
                "TomTom provider is enabled but TOMTOM_API_KEY is not set."
            )
        self._client = TomTomClient(
            self._settings.tomtom_api_key,
            timeout_seconds=float(self._settings.tomtom_timeout_seconds),
        )

    def _location_query(self, city: str, state: str | None) -> str:
        city = city.strip()
        if state and state.strip():
            return f"{city}, {state.strip()}"
        return city

    def search_businesses(
        self,
        category: str,
        city: str,
        state: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> ProviderSearchResult:
        location = self._location_query(city, state)
        effective_limit = min(max(limit, 1), self.max_scan_limit)
        offset = (page - 1) * effective_limit

        logger.info(
            "tomtom_search_requested",
            term=category,
            location=location,
            limit=effective_limit,
            page=page,
            offset=offset,
        )

        try:
            geocode_payload = self._client.geocode(location)
            lat, lon = extract_geocode_position(geocode_payload)
        except ValueError as exc:
            raise ProviderAPIError(str(exc)) from exc

        search_payload = self._client.search_poi(
            term=category.strip(),
            lat=lat,
            lon=lon,
            limit=effective_limit,
            offset=offset,
            radius_meters=self._settings.tomtom_search_radius_meters,
        )

        records = parse_tomtom_search_response(
            search_payload,
            requested_category=category.strip(),
            requested_city=city.strip(),
            requested_state=state.strip() if state else None,
        )

        summary = search_payload.get("summary") or {}
        total = int(summary.get("totalResults") or len(records))

        logger.info(
            "tomtom_search_completed",
            returned=len(records),
            total_reported=total,
            location=location,
            geocoded_lat=lat,
            geocoded_lon=lon,
        )

        return ProviderSearchResult(
            records=records,
            total=total,
            page=page,
            limit=effective_limit,
        )
