"""Mock provider sample businesses — varied website/contact quality."""

from __future__ import annotations

import hashlib

from app.providers.base import BaseProvider, ProviderRecord, ProviderSearchResult

# Each template exercises a different ingestion/dedup scenario.
_TEMPLATES: list[dict] = [
    {
        "suffix": "Family Dental",
        "website": None,
        "phone": "555-0101",
        "street": "101 Main St",
        "postal_code": "90210",
    },
    {
        "suffix": "Smile Studio",
        "website": "https://www.facebook.com/smilestudio",
        "phone": "555-0102",
        "street": "220 Oak Ave",
        "postal_code": "90210",
    },
    {
        "suffix": "Downtown Grill",
        "website": "https://downtowngrill.wixsite.com/menu",
        "phone": "555-0201",
        "street": "45 Market St",
        "postal_code": "90211",
    },
    {
        "suffix": "Harbor Cafe",
        "website": None,
        "phone": "555-0202",
        "street": "8 Pier Rd",
        "postal_code": "90212",
    },
    {
        "suffix": "Quick Auto Repair",
        "website": "http://quickauto.example-local.com",
        "phone": "555-0301",
        "street": "500 Industrial Blvd",
        "postal_code": "90213",
    },
    {
        "suffix": "Elite Plumbing",
        "website": "https://eliteplumbingco.com",
        "phone": "555-0401",
        "street": "12 Cedar Ln",
        "postal_code": "90214",
    },
    {
        "suffix": "Green Leaf Landscaping",
        "website": "https://instagram.com/greenleaf_landscaping",
        "phone": "555-0501",
        "street": "77 Valley Dr",
        "postal_code": "90215",
    },
    {
        "suffix": "Summit Law Group",
        "website": "https://summitlaw.example.com/contact",
        "phone": "555-0601",
        "street": "900 Legal Plaza",
        "postal_code": "90216",
    },
    {
        "suffix": "Corner Market",
        "website": None,
        "phone": None,
        "street": "3rd & Broadway",
        "postal_code": None,
    },
    {
        "suffix": "Family Dental",
        "website": None,
        "phone": "555-0101",
        "street": "101 Main Street",
        "postal_code": "90210",
        "duplicate_of_index": 0,
    },
]


class MockProvider(BaseProvider):
    """Generates deterministic mock businesses for any category + city."""

    name = "mock"
    display_name = "Mock Local Directory"

    def search_businesses(
        self,
        category: str,
        city: str,
        state: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> ProviderSearchResult:
        state = state or "CA"
        seed = f"{category.lower()}:{city.lower()}:{state.lower()}"
        offset = (page - 1) * limit

        records: list[ProviderRecord] = []
        for idx, template in enumerate(_TEMPLATES):
            if idx < offset:
                continue
            if len(records) >= limit:
                break

            name = f"{city} {template['suffix']}"
            if template.get("duplicate_of_index") is not None:
                dup_idx = template["duplicate_of_index"]
                external_id = hashlib.sha256(f"{seed}:{dup_idx}".encode()).hexdigest()[:16]
            else:
                external_id = hashlib.sha256(f"{seed}:{idx}".encode()).hexdigest()[:16]

            records.append(
                ProviderRecord(
                    business_name=name,
                    category=category,
                    city=city,
                    state=state,
                    external_id=external_id,
                    phone=template.get("phone"),
                    email=(
                        f"info{idx}@{city.lower().replace(' ', '')}biz.example"
                        if template.get("phone")
                        else None
                    ),
                    address_line1=template.get("street"),
                    postal_code=template.get("postal_code"),
                    country="US",
                    website_url=template.get("website"),
                    social_links=(
                        {"facebook": template["website"]}
                        if template.get("website") and "facebook.com" in template["website"]
                        else None
                    ),
                    source_url=f"https://mock-directory.local/biz/{external_id}",
                    raw_payload={
                        "mock_index": idx,
                        "seed": seed,
                        "duplicate_of_index": template.get("duplicate_of_index"),
                    },
                )
            )

        return ProviderSearchResult(
            records=records,
            total=len(_TEMPLATES),
            page=page,
            limit=limit,
        )
