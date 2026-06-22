"""HTTP fetch layer for inspection — injectable for tests."""

from __future__ import annotations

import httpx

from app.services.inspection_heuristics import HttpFetchResult


class HttpxFetcher:
    """Default HTTP fetcher using httpx."""

    def __init__(self, user_agent: str = "OIS-Leadfinder/0.1 (+internal)"):
        self.user_agent = user_agent

    def fetch(self, url: str, timeout_seconds: int) -> HttpFetchResult:
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=timeout_seconds,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = client.get(url)
                final_url = str(response.url)
                return HttpFetchResult(
                    final_url=final_url,
                    http_status=response.status_code,
                    reachable=response.status_code < 400,
                    ssl_present=final_url.startswith("https"),
                    html=response.text[:500_000],
                )
        except httpx.HTTPError as exc:
            return HttpFetchResult(reachable=False, error_message=str(exc))


def social_precheck_result(url: str) -> HttpFetchResult:
    """Synthetic fetch result for social-only URLs (no HTTP fetch)."""
    return HttpFetchResult(
        final_url=url,
        http_status=None,
        reachable=True,
        ssl_present=url.startswith("https"),
        html="",
    )
