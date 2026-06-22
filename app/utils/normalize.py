"""Normalization helpers for deduplication and display."""

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_SOCIAL_HOSTS = frozenset(
    {
        "facebook.com",
        "fb.com",
        "instagram.com",
        "linktr.ee",
        "yelp.com",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "youtube.com",
        "linkedin.com",
    }
)

_FREE_HOST_PATTERNS = (
    ".wixsite.com",
    ".wordpress.com",
    ".blogspot.com",
    ".square.site",
    ".weebly.com",
    ".godaddysites.com",
)


def normalize_business_name(name: str) -> str:
    """Lowercase alphanumeric name for dedup comparisons."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def normalize_phone(phone: str | None) -> str | None:
    """Strip phone to digits only."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits or None


def extract_domain(url: str | None) -> str | None:
    """Extract hostname from a URL or bare domain."""
    if not url or not url.strip():
        return None
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return host or None


def normalize_website_url(url: str | None) -> str | None:
    """Return a canonical https URL with tracking params stripped."""
    if not url or not url.strip():
        return None
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    return strip_url_tracking_params(candidate)


def strip_url_tracking_params(url: str) -> str:
    """Remove common marketing/tracking query parameters."""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    drop_prefixes = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")
    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith(drop_prefixes) and k.lower() not in drop_prefixes
    ]
    return urlunparse(parsed._replace(query=urlencode(kept)))


def normalize_state(state: str | None) -> str | None:
    """Normalize US state to uppercase abbreviation when possible."""
    if not state or not state.strip():
        return None
    cleaned = state.strip().upper()
    if len(cleaned) == 2:
        return cleaned
    return cleaned.title()


def normalize_city(city: str | None) -> str | None:
    """Normalize city casing for storage."""
    if not city or not city.strip():
        return None
    return city.strip().title()


def partition_website_and_social(
    website_url: str | None,
    social_links: dict[str, str] | None,
) -> tuple[str | None, dict[str, str] | None]:
    """Move social/directory URLs out of website_url into social_links."""
    links = dict(social_links or {})
    url = normalize_website_url(website_url)
    domain = extract_domain(url)
    if url and is_social_host(domain):
        key = (domain or "social").split(".")[0]
        links.setdefault(key, url)
        url = None
    return url, links or None


def is_social_host(domain: str | None) -> bool:
    """True when domain is a known social/directory host."""
    if not domain:
        return False
    return any(domain == host or domain.endswith(f".{host}") for host in _SOCIAL_HOSTS)


_STREET_ABBREVS = {
    "st": "street",
    "str": "street",
    "street": "street",
    "ave": "avenue",
    "av": "avenue",
    "avenue": "avenue",
    "blvd": "boulevard",
    "boulevard": "boulevard",
    "rd": "road",
    "road": "road",
    "dr": "drive",
    "drive": "drive",
    "ln": "lane",
    "lane": "lane",
}


def normalize_address_line(address: str | None) -> str | None:
    """Normalize a street address for dedup comparisons."""
    if not address or not address.strip():
        return None
    cleaned = re.sub(r"[^a-z0-9\s]", " ", address.lower()).strip()
    tokens = [t for t in re.sub(r"\s+", " ", cleaned).split(" ") if t]
    if not tokens:
        return None
    normalized = [_STREET_ABBREVS.get(token, token) for token in tokens]
    return " ".join(normalized)


def address_dedup_key(
    address_line1: str | None,
    city: str | None,
    state: str | None = None,
    postal_code: str | None = None,
) -> str | None:
    """Build a stable dedup key from address components."""
    street = normalize_address_line(address_line1)
    if not street or not city:
        return None
    city_n = city.lower().strip()
    state_n = (state or "").lower().strip()
    zip_n = re.sub(r"\D", "", postal_code or "")
    return f"{street}|{city_n}|{state_n}|{zip_n}"


def is_free_subdomain(domain: str | None) -> bool:
    """True when domain looks like a free-hosted subdomain."""
    if not domain:
        return False
    return any(domain.endswith(pattern) for pattern in _FREE_HOST_PATTERNS)
