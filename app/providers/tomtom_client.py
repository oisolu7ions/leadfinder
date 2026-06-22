"""TomTom Search API HTTP client (no live calls in unit tests)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.providers.errors import ProviderAPIError, ProviderNotConfiguredError

TOMTOM_SEARCH_BASE = "https://api.tomtom.com/search/2"


class TomTomClient:
    """Thin client for TomTom geocode + POI search."""

    def __init__(self, api_key: str, *, timeout_seconds: float = 15.0) -> None:
        if not api_key or not api_key.strip():
            raise ProviderNotConfiguredError(
                "TomTom provider requires TOMTOM_API_KEY. Set it in .env or disable TOMTOM_ENABLED."
            )
        self._api_key = api_key.strip()
        self._timeout = timeout_seconds

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = dict(params or {})
        query["key"] = self._api_key
        url = f"{TOMTOM_SEARCH_BASE}/{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=query)
        except httpx.RequestError as exc:
            raise ProviderAPIError(f"TomTom API request failed: {exc}") from exc

        if response.status_code in (401, 403):
            raise ProviderAPIError(
                "TomTom API rejected the API key. Check TOMTOM_API_KEY and Search API access.",
                status_code=response.status_code,
            )
        if response.status_code == 429:
            raise ProviderAPIError(
                "TomTom API rate limit exceeded (429). Retry with a smaller batch later.",
                status_code=429,
            )
        if response.status_code >= 400:
            detail = response.text[:300] if response.text else response.reason_phrase
            raise ProviderAPIError(
                f"TomTom API error {response.status_code}: {detail}",
                status_code=response.status_code,
            )

        return response.json()

    def geocode(self, location: str) -> dict[str, Any]:
        """Geocode a city/state string to coordinates."""
        encoded = quote(location.strip(), safe="")
        return self._get(f"geocode/{encoded}.json", params={"limit": 1})

    def search_poi(
        self,
        *,
        term: str,
        lat: float,
        lon: float,
        limit: int,
        offset: int = 0,
        radius_meters: int,
        country_set: str = "US",
    ) -> dict[str, Any]:
        """Search POIs near a point for a category/term."""
        encoded = quote(term.strip(), safe="")
        return self._get(
            f"search/{encoded}.json",
            params={
                "lat": lat,
                "lon": lon,
                "radius": radius_meters,
                "limit": min(max(limit, 1), 50),
                "ofs": max(offset, 0),
                "idxSet": "POI",
                "countrySet": country_set,
            },
        )
