# Leadfinder — OIS Lead Discovery Platform

Internal web-based lead discovery and review platform for finding local businesses that may need websites or better websites.

## Stack

- Python 3.12, FastAPI, SQLAlchemy, Alembic
- PostgreSQL, Redis
- Jinja2 server-rendered dashboard (HTMX in later phases)
- Playwright for optional browser inspection (Phase 3+)
- Docker Compose for local development

## Project layout

```
app/
  api/          # HTTP routes (health, dashboard, future REST)
  core/         # Config, logging
  db/           # SQLAlchemy session, Redis client
  models/       # ORM models
  schemas/      # Pydantic schemas
  providers/    # Lead source adapters
  services/     # Scan, normalization, persistence, inspection, etc.
  workers/      # Background jobs (Phase 8+)
  templates/    # Jinja2 HTML
  static/       # CSS/assets
  utils/
alembic/        # Database migrations
tests/
```

## Quick start (development)

```bash
cd /home/powolabi/projects/leadfinder
cp .env.example .env
docker compose up --build
```

Development Compose (`docker-compose.yml`) bind-mounts source code and enables Uvicorn reload.

- Dashboard: `http://localhost:8000/`
- Health: `http://localhost:8000/health`

## Production deployment (LAN VM)

For persistent internal LAN deployment on Ubuntu, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

Quick production start:

```bash
cp .env.example .env
# Edit .env: APP_ENV=production, DEBUG=false, strong SECRET_KEY and POSTGRES_PASSWORD
./scripts/stack.sh up
# Access from LAN: http://<vm-ip>:8000
```

Services: Postgres, Redis, web app, worker, scheduler — with persistent volumes and automatic migrations.

## Local development (without Docker app container)

Start only Postgres and Redis (if using Docker for infra):

```bash
docker compose up -d db redis
```

Or use system Postgres/Redis already running on the VM.

Create a virtualenv and install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

**Database setup:** With Docker Compose, the default `DATABASE_URL` in `.env.example` works. For system Postgres with peer auth (no `leadfinder` role), create the database and point `.env` at your user:

```bash
createdb leadfinder   # or: psql -d postgres -c "CREATE DATABASE leadfinder;"
# In .env:
# DATABASE_URL=postgresql+psycopg://YOUR_USER@/leadfinder
```

Run migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Database migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Roll back one revision
alembic downgrade -1
```

## Tests

```bash
# Requires Postgres + Redis running (docker compose up -d db redis)
pytest -v
```

Health/liveness tests work without DB; dashboard and full health check need Postgres.

## Environment variables

See `.env.example`. Key settings:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `LOG_LEVEL` | `DEBUG`, `INFO`, etc. |
| `LOG_FORMAT` | `console` or `json` |
| `WORKER_CONCURRENCY` | Background worker parallelism (Phase 8) |
| `INSPECTION_BROWSER_ENABLED` | Enable Playwright inspection (Phase 3) |

## Implementation phases

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | **Done** | Foundation, models, migrations, health, Docker Compose |
| 2 | **Done** | Mock provider ingestion, scan jobs, dedup, full dashboard |
| 3 | **Done** | HTTP + optional Playwright inspection, Redis queue, worker |
| 4 | **Done** | Transparent rule-based scoring with breakdown and priority tiers |
| 5 | **Done** | Operational dashboard UI — KPIs, badges, filters, settings, shared partials |
| 6 | **Done** | Template-based outreach drafts with review-only workflow |
| 7 | **Done** | CSV exports with filters, history, secure downloads, full column set |
| 8 | Planned | Scheduled scans + Redis background workers |
| 9 | Planned | Ubuntu VM production deployment |

## Dashboard

Server-rendered internal UI at `/`:

| Page | URL | Features |
|------|-----|----------|
| Home | `/` | Summary cards, recent scans, recent leads |
| Scans | `/scans` | Run scan form, job history |
| Scan detail | `/scans/{id}` | Job stats, linked leads |
| Leads | `/leads` | Filterable/searchable table, bulk inspect |
| Lead detail | `/leads/{id}` | Contact info, inspection, score, outreach drafts |
| Exports | `/exports` | CSV export with filters, download history |

## Phase 2 — Lead ingestion

### Architecture

```
Provider (mock, tomtom when enabled, etc.)
    → search_businesses(category, city, state, limit, page)
    → ProviderRecord (raw provider shape)
Normalization (lead_normalization.py)
    → NormalizedLeadData
Persistence (lead_persistence.py)
    → dedup + insert/update BusinessLead
Scan service (scan.py)
    → ScanJob lifecycle + metrics
```

### Dedup order

1. `(source_name, external_id)`
2. Normalized phone
3. Normalized domain
4. Normalized address key (`street|city|state|zip`)
5. Normalized business name + city

Repeated scans update existing leads instead of creating duplicates.

### REST API (internal)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scans` | Create scan (`run_immediately` defaults to `true`) |
| `POST` | `/api/scans/{id}/run` | Run a pending scan |
| `GET` | `/api/scans` | List recent scan jobs |
| `GET` | `/api/scans/{id}` | Scan job detail |
| `GET` | `/api/leads` | List leads (filterable) |
| `GET` | `/api/leads/{id}` | Lead detail |

Example:

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{"category":"dentist","city":"Austin","state":"TX","limit":10}'

curl "http://localhost:8000/api/leads?city=Austin"
```

### Manual verification

1. Start the app (`uvicorn app.main:app --reload`)
2. Open `/scans` → run scan: category `restaurant`, city `Chicago`, state `IL`, limit `10`
3. Confirm scan completes with inserted/updated counts
4. Open `/leads?city=Chicago` → see ingested businesses
5. Run the same scan again → `total_updated` should increase, lead count unchanged
6. Try API: `POST /api/scans` and `GET /api/leads?city=Chicago`

## Phase 3 — Website inspection

### Pipeline

```
Lead → prechecks (no network)
     → HTTP fetch + HTML heuristics (default)
     → optional Playwright (INSPECTION_BROWSER_ENABLED=true)
     → WebsiteInspection persisted + optional auto-score
```

Modules: `inspection_heuristics`, `inspection_http`, `browser_inspector`, `inspection_service`, `inspection_queue`.

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/inspections/leads/{id}` | Run inspection now (sync) |
| `POST` | `/api/inspections/leads/{id}/queue` | Queue for background worker |
| `POST` | `/api/inspections/queue` | Queue batch `{lead_ids}` or `{uninspected_limit}` |
| `GET` | `/api/inspections` | List inspections |
| `GET` | `/api/inspections/{id}` | Inspection detail |
| `GET` | `/api/inspections/leads/{id}/history` | Lead inspection history |

### Background worker

```bash
# Terminal 1 — app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — inspection worker (processes Redis queue, one job at a time)
python -m app.workers.inspection_worker

# Or with Docker Compose
docker compose up inspection-worker
```

### Config (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `INSPECTION_BROWSER_ENABLED` | `false` | Enable Playwright |
| `INSPECTION_BROWSER_CONCURRENCY` | `1` | Max concurrent browser sessions |
| `INSPECTION_TIMEOUT_SECONDS` | `30` | HTTP/browser timeout |
| `INSPECTION_QUEUE_NAME` | `leadfinder:inspection:queue` | Redis queue key |
| `INSPECTION_SAVE_ARTIFACTS` | `true` | Save screenshots/HTML snapshots |

### Manual verification

1. Run a scan to ingest leads (`/scans`)
2. Open a lead → **Run inspection now** (sync) or **Queue inspection**
3. View results on lead detail or `/inspections/{id}`
4. API: `POST /api/inspections/leads/1` with optional `{"run_browser": false}`
5. Queue batch: `POST /api/inspections/queue` `{"uninspected_limit": 10}` then start worker

## Phase 4 — Lead scoring

### Scoring matrix (tune in `app/services/scoring_rules.py`)

| Signal | Points |
|--------|--------|
| No website | 35 |
| Social-only presence | 30 |
| Free subdomain / weak branding | 15 |
| Non-branded domain | 10 |
| Unreachable site | 15 |
| No SSL (HTTPS) | 8 |
| Poor mobile basics | 12 |
| No contact page / CTA | 12 |
| No booking flow (booking-sensitive categories) | 10 |
| Weak/outdated (missing title when reachable) | 8 |

**Priority tiers:** High ≥ 50 · Medium 25–49 · Low &lt; 25

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scoring/leads/{id}` | Score lead |
| `POST` | `/api/scoring/leads/{id}/rescore` | Rescore with latest inspection |
| `GET` | `/api/scoring/leads/{id}` | Latest score + breakdown |
| `GET` | `/api/scoring/leads/{id}/history` | Score history |
| `POST` | `/api/scoring/bulk/unscored` | Score leads without scores |
| `POST` | `/api/scoring/bulk/rescore-inspected` | Rescore inspected leads |

### Manual verification

1. Inspect a lead (or use one with no website from mock scan)
2. Click **Score lead** or `POST /api/scoring/leads/{id}`
3. View breakdown on lead detail — sub-scores, factors, priority badge
4. Filter leads by priority or sort by score on `/leads`
5. **Score unscored** from leads page for bulk scoring

## Phase 5 — Dashboard UI

Operational internal console with DB-backed pages, shared components, and consistent badges.

### Pages

| Path | Purpose |
|------|---------|
| `/` | Lead Discovery Dashboard — KPIs, needs-review queue, recent activity, sidebar summaries |
| `/leads` | Primary lead workspace — filters, sort by score, row actions |
| `/leads/{id}` | Lead detail — 2-column layout with score breakdown and inspection summary |
| `/scans` | Run scans and review job history |
| `/scans/{id}` | Scan detail with linked leads |
| `/inspections` | Inspection list with filters |
| `/inspections/{id}` | Inspection detail with collapsible raw JSON |
| `/exports` | CSV export form and history |
| `/settings` | Environment, inspection, storage, provider info (no secrets) |

### Shared UI partials (`app/templates/partials/ui/`)

- `page_header.html` — title, subtitle, action slot
- `stat_card.html` — KPI cards
- `badge.html` — consistent badge rendering
- `empty_state.html` — empty DB states with CTAs
- `detail_card.html` — bordered section cards
- `collapsible.html` — raw JSON / long content
- `post_button.html` — CSRF POST action helper

Badge logic lives in `app/services/ui_presenters.py` (not templates).

Dashboard metrics are assembled in `app/services/dashboard_service.py`.

### Manual verification

1. Open `/` — confirm KPI cards, needs-review queue, sidebar summaries
2. Run a scan from `/` or `/scans`, confirm recent scan table updates
3. Open `/leads` — filter by priority, sort by score, use row Inspect/Score actions
4. Open a lead — verify 2-column layout, score breakdown, collapsible raw JSON
5. Open `/inspections` — apply reachable/social filters
6. Open `/settings` — confirm env and browser flags (no secret key shown)

## Phase 6 — Outreach drafts

Review-only outreach generation from stored lead, inspection, and score data. **Nothing is auto-sent.**

### Template strategy

Findings are detected in priority order (`app/services/outreach_templates.py`):

1. No website
2. Social-only presence
3. Unreachable site
4. Weak / non-branded domain
5. Missing contact path
6. Missing booking flow (booking-sensitive categories only)
7. Poor mobile basics
8. General weak presence (fallback)

The **primary angle** drives subject line and benefit copy; up to two secondary findings may appear in the email observation sentence. Subject lines use deterministic variation by lead ID.

**Regenerate** creates a **new** `OutreachDraft` row — previous drafts are preserved for traceability.

### Statuses

| Status | Meaning |
|--------|---------|
| `draft_ready` | Generated, awaiting human review |
| `reviewed` | Marked reviewed in UI |
| `archived` | Archived / no longer active |

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/outreach/leads/{id}` | Generate draft |
| `POST` | `/api/outreach/leads/{id}/regenerate` | Regenerate (new record) |
| `GET` | `/api/outreach/leads/{id}/latest` | Latest draft for lead |
| `GET` | `/api/outreach/drafts` | List drafts |
| `GET` | `/api/outreach/drafts/{id}` | View draft |
| `POST` | `/api/outreach/drafts/{id}/reviewed` | Mark reviewed |
| `PATCH` | `/api/outreach/drafts/{id}/status` | Update status |

### Manual verification

1. Run a scan and inspect/score a lead
2. Open lead detail → **Generate Draft**
3. Review subject, email, DM, call notes, and “Why this angle”
4. **Regenerate Draft** — confirm a new draft appears in history
5. **Mark Reviewed** — status updates in UI and `/outreach` list
6. Browse `/outreach` for all drafts

## Phase 7 — CSV exports

Flat CSV exports of lead pipeline data with filters, history, and secure downloads.

### CSV columns

Lead basics, inspection summary, score summary, and outreach summary — see `EXPORT_CSV_COLUMNS` in `app/services/export_serializers.py`.

Key columns: `lead_id`, `business_name`, `city`, `website_url`, `inspection_status`, `reachable`, `social_only`, `total_score`, `priority_tier`, `outreach_status`, `latest_draft_subject_line`.

### Filters

Reuses `LeadFilters` / `build_leads_query` — same filters as the Leads page plus inspection-specific filters:

- `insp_reachable`, `insp_social_only`, `insp_blank_website`, `insp_has_contact_page`, `insp_has_booking_flow`
- `priority`, `source_name`, `outreach_status`, score min/max, etc.

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/exports` | Create and run export (`{"filters": {"city": "Austin"}}`) |
| `GET` | `/api/exports` | List export jobs |
| `GET` | `/api/exports/{id}` | Export job detail |
| `GET` | `/api/exports/{id}/download` | Download CSV |

### Manual verification

1. Open `/exports` → fill filters → **Create Export**
2. Confirm job appears in history with row count and status `completed`
3. Click **Download** — open CSV in spreadsheet app
4. From `/leads`, apply filters → **Export Current View**
5. Open `/exports/{id}` for filter details

Files stored under `EXPORT_DIR` (default `./data/exports`).

## Phase 8 — Scheduling + Workers

Background processing for heavy workflows using a **unified Redis job queue**, a **single worker process** (conservative concurrency), and **DB-backed scheduled tasks**.

### Architecture

```
Web/API action → enqueue (IDs + params) → Redis queue
Worker (python -m app.workers.worker) → handle_job → existing services
Scheduler (python -m app.scheduler.runner) → due ScheduledTask → enqueue
```

| Module | Role |
|--------|------|
| `app/workers/queue.py` | Generic Redis queue (`JobEnvelope`, retry/requeue) |
| `app/workers/enqueue.py` | Thin enqueue helpers per job type |
| `app/workers/jobs/handlers.py` | Dispatches to `run_scan_job`, `inspect_lead`, etc. |
| `app/workers/worker.py` | Worker loop (one job at a time by default) |
| `app/scheduler/service.py` | `ScheduledTask` CRUD + due-task tick |
| `app/scheduler/runner.py` | Scheduler process |
| `app/api/background_routes.py` | Enqueue + schedule REST API |
| `app/models/scheduled_task.py` | Recurring task records |

Legacy `INSPECTION_QUEUE_NAME` payloads are still consumed (drained via `LPOP` before the unified queue).

### Job types (queue name: `JOB_QUEUE_NAME`, default `leadfinder:jobs:queue`)

| Type | Payload | Service |
|------|---------|---------|
| `scan` | `scan_job_id`, `limit` | `run_scan_job` |
| `inspect` | `lead_id`, `auto_score` | `inspect_lead` |
| `inspect_bulk` | `lead_ids` and/or `uninspected_limit` | loop `inspect_lead` |
| `score` | `lead_id` | `score_lead` |
| `score_bulk` | `limit` | `score_unscored_leads` |
| `outreach` | `lead_id` | `generate_draft` |
| `export` | `export_job_id` | `run_export_job` |

### Scheduled task types

| Type | Enqueues |
|------|----------|
| `scan` | Scan job (payload: category, city, source_name, limit) |
| `inspect_unreviewed` | Bulk inspection of uninspected leads |
| `score_unscored` | Bulk scoring |
| `export` | Export job (optional; payload.filters) |

Manage schedules at `/schedules` or via `POST /api/background/schedules`.

### Config (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `JOB_QUEUE_NAME` | `leadfinder:jobs:queue` | Unified Redis queue key |
| `JOB_MAX_RETRIES` | `3` | Max attempts per job |
| `JOB_RETRY_DELAY_SECONDS` | `5` | Delay before retry requeue |
| `WORKER_POLL_SECONDS` | `5` | Worker BLPOP timeout |
| `SCHEDULER_POLL_SECONDS` | `60` | Scheduler tick interval |
| `WORKER_CONCURRENCY` | `2` | Reserved for future use; worker runs one job at a time |
| `INSPECTION_BROWSER_CONCURRENCY` | `1` | Keep low on 6 vCPU / 12 GB VM |

### Run commands

```bash
# Web app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Background worker (processes all job types, one at a time)
python -m app.workers.worker

# Scheduler (enqueues due scheduled tasks)
python -m app.scheduler.runner

# Docker Compose (app + worker + scheduler)
docker compose up app worker scheduler
```

Migration: `alembic upgrade head` (revision `006_scheduled_tasks`).

### REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/background/queue` | Queue depth stats |
| `POST` | `/api/background/scans` | Create + enqueue scan |
| `POST` | `/api/background/inspections/leads/{id}` | Enqueue inspection |
| `POST` | `/api/background/inspections/bulk` | Enqueue bulk inspection |
| `POST` | `/api/background/scoring/leads/{id}` | Enqueue score |
| `POST` | `/api/background/scoring/bulk/unscored` | Enqueue bulk score |
| `POST` | `/api/background/outreach/leads/{id}` | Enqueue outreach draft |
| `POST` | `/api/background/exports` | Create + enqueue export |
| `GET/POST/PATCH` | `/api/background/schedules` | List/create/update schedules |

Scan/export APIs also support queue mode: `POST /api/scans` with `"run_immediately": false`, `POST /api/exports` with `"run_immediately": false`.

### Manual verification

1. Start app, worker, and optionally scheduler
2. `/scans` → **Queue Scan** → confirm ScanJob stays `pending` until worker runs
3. `/exports` → **Queue Export** → job shows `pending`, then `completed` after worker
4. Lead detail → **Queue Inspection** → worker processes and persists inspection
5. `/schedules` → create recurring inspect/score task → scheduler enqueues on interval
6. `/` sidebar → **Background Queue** shows pending count
7. `GET /api/background/queue` → verify stats

### Mock provider samples

The mock provider returns 10 templates including:

- No website (dental, cafe, corner market)
- Facebook-only URL
- Free subdomain (Wix)
- Branded domain
- Instagram-only URL
- Missing phone / partial address
- Duplicate dental entry (same business, address variant — deduped)

## Phase 9 — LAN Deployment

Production-ready internal deployment for an Ubuntu VM on your private LAN. **Not internet-facing.**

Full guide: **[DEPLOYMENT.md](DEPLOYMENT.md)**

### Stack (production Compose)

| Service | Purpose |
|---------|---------|
| `db` | PostgreSQL — volume `leadfinder_pgdata` |
| `redis` | Redis AOF — volume `leadfinder_redis_data` |
| `migrate` | One-shot Alembic on startup |
| `app` | Web UI/API — LAN port 8000 |
| `worker` | Background jobs |
| `scheduler` | Recurring tasks |
| `nginx` (optional) | Internal reverse proxy port 80 |

### Quick commands

```bash
cp .env.example .env   # set production secrets
./scripts/stack.sh up
./scripts/stack.sh health
./scripts/stack.sh logs-worker
./scripts/stack.sh backup
./scripts/stack.sh update   # pull, rebuild, migrate, restart
```

Optional Nginx: `./scripts/stack.sh proxy-up` → `http://<vm-ip>/`

Boot on startup: `deploy/systemd/leadfinder.service`

## Phase 10 — Live provider (TomTom Search)

Adds **one real provider** behind the existing abstraction. **Mock provider unchanged** for tests and debugging.

Full rollout guide: **[docs/LIVE_ROLLOUT.md](docs/LIVE_ROLLOUT.md)**

### Quick enable

```bash
# In .env
TOMTOM_ENABLED=true
TOMTOM_API_KEY=your-tomtom-search-api-key
```

Restart the app → **Scans** → select **TomTom Search (Live)** → run with limit **10–25**.

### Safe defaults

- Live scans default to **15** records in UI
- Hard cap **50** per scan request
- Raw TomTom payloads stored on each `BusinessLead`
- Reruns dedupe by TomTom `external_id`, phone, and address keys

### Verify

```bash
pytest tests/test_tomtom_provider.py tests/test_normalize_real_data.py -v
```

## Phase 1 deliverables

- FastAPI application with structured logging
- All core entity models and initial Alembic migration
- `/health`, `/health/live`, `/health/ready` endpoints
- Dashboard home with summary cards and recent scans table
- Docker Compose (Postgres, Redis, app)
- Basic pytest suite

## License

Internal OIS tool — not for public distribution.
