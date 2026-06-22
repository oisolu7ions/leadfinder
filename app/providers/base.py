"""Abstract interface for lead data source providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderRecord:
    """Raw business record returned by a provider search."""

    business_name: str
    category: str
    city: str
    external_id: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"
    website_url: str | None = None
    social_links: dict[str, str] | None = None
    source_url: str | None = None
    raw_payload: dict | None = field(default_factory=dict)


@dataclass
class ProviderSearchResult:
    """Paginated provider search response."""

    records: list[ProviderRecord]
    total: int
    page: int
    limit: int


class BaseProvider(ABC):
    """Base class for lead ingestion providers."""

    name: str
    display_name: str
    is_live: bool = False
    default_scan_limit: int = 50
    max_scan_limit: int = 500

    @abstractmethod
    def search_businesses(
        self,
        category: str,
        city: str,
        state: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> ProviderSearchResult:
        """Search for businesses matching category and location."""


# Alias used in ingestion docs — provider output before internal normalization.
NormalizedBusinessRecord = ProviderRecord
