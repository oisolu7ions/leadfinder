"""Cheap website inspection heuristics — no browser required."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse

from app.utils.normalize import (
    extract_domain,
    is_free_subdomain,
    is_social_host,
    normalize_website_url,
)

_CONTACT_KEYWORDS = re.compile(
    r"\b(contact|get in touch|reach us|email us|call us|contact us)\b",
    re.IGNORECASE,
)
_BOOKING_KEYWORDS = re.compile(
    r"\b(book|booking|schedule|appointment|reserve|reservation|order online|book now)\b",
    re.IGNORECASE,
)
_VIEWPORT_META = re.compile(
    r'<meta[^>]+name=["\']viewport["\']',
    re.IGNORECASE,
)
_CONTACT_PATH = re.compile(r"/(contact|contact-us|about/contact)(/|$)", re.IGNORECASE)

_GOOGLE_BUSINESS_HOSTS = frozenset(
    {
        "google.com",
        "business.google.com",
        "maps.google.com",
        "g.page",
        "goo.gl",
    }
)


@dataclass
class HtmlAnalysis:
    page_title: str | None = None
    meta_description: str | None = None
    has_contact_page: bool = False
    has_booking_flow: bool = False
    mobile_friendly_basic: bool = False
    contact_links: list[str] = field(default_factory=list)


@dataclass
class HttpFetchResult:
    final_url: str | None = None
    http_status: int | None = None
    reachable: bool = False
    ssl_present: bool = False
    html: str = ""
    error_message: str | None = None


@dataclass
class PrecheckResult:
    website_url: str | None
    domain: str | None
    blank_website: bool
    social_only: bool
    branded_domain: bool
    checks: list[str] = field(default_factory=list)


class HttpFetcher(Protocol):
    def fetch(self, url: str, timeout_seconds: int) -> HttpFetchResult: ...


def is_google_business_url(url: str | None, domain: str | None) -> bool:
    """Detect Google Business / Maps listing URLs."""
    if not url and not domain:
        return False
    host = domain or extract_domain(url)
    if not host:
        return False
    if any(host == h or host.endswith(f".{h}") for h in _GOOGLE_BUSINESS_HOSTS):
        return True
    if url and ("google.com/maps" in url or "business.google.com" in url):
        return True
    return False


def is_social_or_directory_url(url: str | None, domain: str | None) -> bool:
    """True for social hosts, link-in-bio, Yelp, or Google business listings."""
    if not url:
        return False
    return is_social_host(domain) or is_google_business_url(url, domain)


def run_prechecks(website_url: str | None) -> PrecheckResult:
    """First-pass checks without network or browser."""
    url = normalize_website_url(website_url)
    domain = extract_domain(url)
    checks: list[str] = []

    if not url:
        return PrecheckResult(
            website_url=None,
            domain=None,
            blank_website=True,
            social_only=False,
            branded_domain=False,
            checks=["blank_website"],
        )

    social_only = is_social_or_directory_url(url, domain)
    branded = bool(domain) and not is_free_subdomain(domain) and not social_only
    checks.append("social_only" if social_only else "has_website_url")
    if branded:
        checks.append("branded_domain")
    elif domain and is_free_subdomain(domain):
        checks.append("free_subdomain")

    return PrecheckResult(
        website_url=url,
        domain=domain,
        blank_website=False,
        social_only=social_only,
        branded_domain=branded,
        checks=checks,
    )


def analyze_html(html: str, page_url: str | None = None) -> HtmlAnalysis:
    """Extract signals from HTML content."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    meta_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html,
        re.IGNORECASE,
    )
    contact_links = _CONTACT_PATH.findall(html)
    has_contact = bool(_CONTACT_KEYWORDS.search(html)) or bool(contact_links)
    return HtmlAnalysis(
        page_title=title_match.group(1).strip()[:500] if title_match else None,
        meta_description=meta_match.group(1).strip()[:2000] if meta_match else None,
        has_contact_page=has_contact,
        has_booking_flow=bool(_BOOKING_KEYWORDS.search(html)),
        mobile_friendly_basic=bool(_VIEWPORT_META.search(html)),
        contact_links=list({m[0] if isinstance(m, tuple) else m for m in contact_links})[:5],
    )


def extract_internal_links(html: str, base_url: str, limit: int = 3) -> list[str]:
    """Return a few obvious top-level internal links (contact/about)."""
    from urllib.parse import urljoin

    links: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        base = urlparse(base_url)
        if parsed.netloc and parsed.netloc != base.netloc:
            continue
        path = (parsed.path or "").lower()
        if any(k in path for k in ("contact", "book", "appointment", "schedule")):
            links.append(full)
        if len(links) >= limit:
            break
    return links


def merge_html_analysis(primary: HtmlAnalysis, secondary: HtmlAnalysis) -> HtmlAnalysis:
    """Combine analyses — true if either source detected a signal."""
    return HtmlAnalysis(
        page_title=primary.page_title or secondary.page_title,
        meta_description=primary.meta_description or secondary.meta_description,
        has_contact_page=primary.has_contact_page or secondary.has_contact_page,
        has_booking_flow=primary.has_booking_flow or secondary.has_booking_flow,
        mobile_friendly_basic=primary.mobile_friendly_basic or secondary.mobile_friendly_basic,
        contact_links=primary.contact_links or secondary.contact_links,
    )
