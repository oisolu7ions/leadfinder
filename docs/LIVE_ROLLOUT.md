# Live Provider Rollout — TomTom Search API

Careful rollout guide for ingesting **real** local business data. The **mock provider remains the default** for tests and debugging.

## Chosen provider: TomTom Search API

**Why TomTom:**
- Controlled category + location search (geocode city/state, then POI search by term)
- Stable POI IDs for dedup (`external_id`)
- Phone, address, and optional website fields for normalization and dedup validation
- Single API key, no OAuth for read-only search
- Good fit for small, conservative live batches at this stage

**Not in scope this phase:** Yelp, Google Places, multiple live providers, large-scale scraping.

---

## Enable the live provider

1. Create a TomTom developer account: https://developer.tomtom.com/
2. Create a project and copy the **Search API** key
3. Edit `.env`:

```bash
TOMTOM_ENABLED=true
TOMTOM_API_KEY=your-api-key-here
# Optional tuning:
TOMTOM_TIMEOUT_SECONDS=15
TOMTOM_SEARCH_RADIUS_METERS=15000
```

4. Restart the web app (and worker if using queued scans)
5. Confirm on **Settings** → TomTom live provider = **Enabled**
6. Confirm **Scans** provider dropdown shows **TomTom Search (Live)**

**Disable anytime:**

```bash
TOMTOM_ENABLED=false
```

Restart the app — only **Mock Local Directory** remains in the provider list.

---

## First live scan (safe pattern)

Use the **Scans** page or API with **small limits**:

| Field | Example |
|-------|---------|
| Provider | TomTom Search (Live) |
| Category | `barbers` |
| City | `Charlotte` |
| State | `NC` |
| Limit | **15** (default when live provider selected) |

Click **Queue Scan** (recommended) or **Run Now (sync)**.

### API example

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{
    "category": "barbers",
    "city": "Charlotte",
    "state": "NC",
    "source_name": "tomtom",
    "limit": 15,
    "run_immediately": true
  }'
```

Live scans are capped at **50** records per request (`max_scan_limit`).

---

## Verification checklist

After each small live scan:

1. **Scan job** — `/scans/{id}`: status `completed`, sensible `logs_summary`
2. **Counts** — `total_found`, `inserted`, `updated`, `flagged` (no website)
3. **Leads** — `/leads?city=Charlotte&source_name=tomtom`
4. **Raw payload** — lead detail → collapsible raw JSON includes `provider: tomtom`, `tomtom_search_hit`
5. **Normalization** — business names, city/state, phone digits look correct
6. **Website handling** — missing or social URLs handled per normalization rules

### Dedup rerun test

Run the **same** category + city + state again with the same limit:

- Expect `total_inserted` ≈ **0**
- Expect `total_updated` ≈ previous insert count
- Lead count in UI should **not** double

Dedup order: `external_id` (TomTom POI ID) → phone → domain → address key → name+city.

---

## Rollback / fallback

| Situation | Action |
|-----------|--------|
| Bad live data batch | Filter leads by `source_name=tomtom`, review/delete manually if needed |
| API errors / quota | Set `TOMTOM_ENABLED=false`, use **mock** provider |
| Invalid key | Fix `TOMTOM_API_KEY`; failed scans show error on ScanJob |
| Need repeatable tests | Always use `source_name: mock` |

---

## Troubleshooting

| Error | Likely cause |
|-------|----------------|
| Provider not in dropdown | `TOMTOM_ENABLED=false` or missing `TOMTOM_API_KEY` |
| `403` on scan | Invalid API key or Search API not enabled for key |
| Geocode returned no results | City/state typo or unsupported location string |
| `Unknown provider: tomtom` | Env not loaded — restart app after `.env` change |
| Duplicate explosion | Report bug — dedup should match TomTom `external_id` |

Check logs for `tomtom_search_requested` / `tomtom_search_completed` / `scan_job_completed`.

---

## Pipeline tuning (Phase 10)

Real-data adjustments included:

- **Social/directory URLs** moved from `website_url` → `social_links` (Facebook, Instagram, Yelp, etc.)
- **Tracking params** stripped from URLs (`utm_*`, `gclid`, …)
- **State** normalized to uppercase (e.g. `nc` → `NC`)
- **City** title-cased for consistency
- **Phone** digits-only for dedup
- **Live scan limits** enforced per provider (`default_scan_limit=15`, `max=50`)

---

## Automated tests (no network)

```bash
pytest tests/test_tomtom_provider.py tests/test_normalize_real_data.py -v
```

Uses fixtures under `tests/fixtures/tomtom/` — no live TomTom calls.
