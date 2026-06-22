# Leadfinder — LAN Deployment Guide

Internal deployment guide for running Leadfinder on an **Ubuntu VM on your private LAN**. This app is **not designed for public internet exposure** — no public DNS, port forwarding, or TLS automation is required.

## Deployment model

**Default: Docker Compose production stack** (`docker-compose.prod.yml`)

| Service | Role |
|---------|------|
| `db` | PostgreSQL 16 — persistent `pgdata` volume |
| `redis` | Redis 7 — persistent AOF (`redis_data` volume) |
| `migrate` | One-shot Alembic migrations on startup |
| `app` | FastAPI web UI + API |
| `worker` | Background job processor |
| `scheduler` | Recurring scheduled tasks |
| `nginx` (optional) | Internal reverse proxy on port 80 |

**Why Compose:** Repeatable startup, isolated dependencies, named volumes for persistence, health checks, and `restart: unless-stopped` for crash recovery.

**Direct access (default):** `http://<vm-lan-ip>:8000`  
**Optional Nginx:** `http://<vm-lan-ip>/` (profile `proxy`)

---

## Architecture

```
LAN clients (browser)
        │
        ▼
  ┌─────────────┐     optional      ┌──────────┐
  │   :8000     │ ◄── Nginx :80 ─── │  nginx   │
  │     app     │                   └──────────┘
  └──────┬──────┘
         │
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
   db      redis    app_data volume
                  (exports, screenshots, snapshots)
    ▲         ▲
 worker   scheduler
```

Postgres and Redis bind to **127.0.0.1** on the VM only (admin/debug). The app binds to **0.0.0.0:8000** for LAN access.

---

## First-time setup (Ubuntu VM)

### 1. Prerequisites

```bash
# Docker Engine + Compose plugin
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git curl
sudo usermod -aG docker $USER
# Log out and back in so docker group applies
```

### 2. Clone and configure

```bash
sudo mkdir -p /opt/leadfinder
sudo chown $USER:$USER /opt/leadfinder
git clone <your-repo-url> /opt/leadfinder
cd /opt/leadfinder

cp .env.example .env
```

Edit `.env` for production:

```bash
APP_ENV=production
DEBUG=false
LOG_FORMAT=json
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 24)
# DATABASE_URL is overridden by Compose for container services
```

**Never commit `.env`.** Back it up separately (see Backup section).

### 3. Start the stack

```bash
chmod +x scripts/*.sh
./scripts/stack.sh up
```

Or manually:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Find your LAN URL

On the VM:

```bash
hostname -I | awk '{print $1}'
```

From another device on the same LAN: `http://192.168.x.x:8000`

### 5. Verify

```bash
./scripts/stack.sh health
./scripts/stack.sh ps
```

Expected:

- `/health/live` → `{"status":"alive"}`
- `/health/ready` → `{"status":"ready"}`
- `/health` → `database: ok`, `redis: ok`

Open the dashboard, queue a scan, confirm the worker processes it (see Worker verification below).

---

## Daily operations

### Start / stop / restart

```bash
./scripts/stack.sh up          # first start or after down
./scripts/stack.sh down        # stop all services
./scripts/stack.sh restart     # restart app, worker, scheduler
./scripts/stack.sh ps          # service status
```

### Logs

All services log to **stdout** (structured JSON when `LOG_FORMAT=json`). View via Docker:

```bash
./scripts/stack.sh logs           # all services, follow
./scripts/stack.sh logs-app       # web app only
./scripts/stack.sh logs-worker    # worker only
./scripts/stack.sh logs-sched     # scheduler only
```

Or directly:

```bash
docker compose -f docker-compose.prod.yml logs -f --tail=200 worker
```

There is no separate log file by default — use `docker logs` or redirect if you need files.

### Migrations

Migrations run automatically on stack startup (`migrate` service + app entrypoint). To run manually:

```bash
./scripts/stack.sh migrate
# or
docker compose -f docker-compose.prod.yml run --rm migrate
```

---

## Optional internal Nginx (port 80)

For cleaner LAN URLs without `:8000`:

```bash
./scripts/stack.sh proxy-up
# Access: http://<vm-lan-ip>/
```

Stop:

```bash
./scripts/stack.sh proxy-down
```

Nginx config: `deploy/nginx/leadfinder.conf` — internal proxy only, no TLS.

---

## Start on boot (systemd)

```bash
sudo cp deploy/systemd/leadfinder.service /etc/systemd/system/
# Edit WorkingDirectory if not /opt/leadfinder
sudo systemctl daemon-reload
sudo systemctl enable --now leadfinder
sudo systemctl status leadfinder
```

Docker's `restart: unless-stopped` also restarts individual containers after crashes or Docker daemon restart.

---

## Persistent storage

| What | Location | Backup? |
|------|----------|---------|
| PostgreSQL | Docker volume `leadfinder_pgdata` | **Yes — critical** |
| Redis queue state | Docker volume `leadfinder_redis_data` | Optional (jobs re-queueable) |
| Exports, screenshots, snapshots | Docker volume `leadfinder_app_data` → `/app/data` | **Yes** |
| Environment secrets | Host file `.env` | **Yes — secure store** |
| Application source | Git repo | Yes (via git remote) |

Inside the app container:

- `DATA_DIR=/app/data`
- `EXPORT_DIR=/app/data/exports`
- Screenshots: `/app/data/screenshots`
- HTML snapshots: `/app/data/snapshots`

Inspect volumes:

```bash
docker volume ls | grep leadfinder
docker run --rm -v leadfinder_app_data:/data alpine ls -la /data
```

---

## Backup and recovery

### Automated backup script

```bash
./scripts/stack.sh backup
```

Creates in `./backups/` (override with `BACKUP_DIR`):

- `leadfinder_db_YYYYMMDD_HHMMSS.sql` — Postgres dump
- `leadfinder_data_YYYYMMDD_HHMMSS.tar.gz` — exports + artifacts

Also back up `.env` to a secure location (password manager, encrypted USB).

### Manual Postgres dump

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U leadfinder leadfinder > backup.sql
```

### Restore Postgres (basic)

```bash
# Stack must be running; DB will be overwritten — test on a copy first
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U leadfinder -d leadfinder < backup.sql
```

### Restore app data volume

```bash
docker run --rm \
  -v leadfinder_app_data:/data \
  -v "$PWD/backups:/backup" \
  alpine sh -c "cd /data && tar xzf /backup/leadfinder_data_YYYYMMDD_HHMMSS.tar.gz"
```

---

## Update / redeploy

From the repo on the VM:

```bash
cd /opt/leadfinder
./scripts/stack.sh update
```

This runs: `git pull` → rebuild images → migrate → restart app/worker/scheduler → health check.

Manual steps:

```bash
git pull --ff-only
docker compose -f docker-compose.prod.yml build app worker scheduler migrate
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d app worker scheduler
./scripts/stack.sh health
```

---

## Environment variables

See `.env.example` for the full list. Production essentials:

| Variable | Notes |
|----------|-------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | Random 32+ bytes — CSRF/session signing |
| `POSTGRES_PASSWORD` | Required by prod Compose |
| `LOG_FORMAT` | `json` recommended |
| `UVICORN_WORKERS` | Default `1` on 6 vCPU VM |
| `INSPECTION_BROWSER_ENABLED` | `false` unless Playwright is in the image |
| `APP_BIND` / `APP_PORT` | LAN bind (default `0.0.0.0:8000`) |

Compose overrides `DATABASE_URL` and `REDIS_URL` to use internal service hostnames.

---

## Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /health/live` | Process alive (liveness) |
| `GET /health/ready` | DB + Redis reachable (readiness) |
| `GET /health` | Full status JSON |

Compose health check on `app` uses `/health/ready`.

---

## Verification checklist

After deploy or update:

```bash
# 1. Services running
./scripts/stack.sh ps

# 2. Health
./scripts/stack.sh health

# 3. LAN access (from another device)
curl http://<vm-ip>:8000/health

# 4. Worker processing
#    Queue a scan from UI → ./scripts/stack.sh logs-worker → see worker_processing

# 5. Scheduler (if schedules configured)
./scripts/stack.sh logs-sched

# 6. Export persistence
#    Queue export → wait → download CSV → restart stack → file still available
./scripts/stack.sh restart
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| UI unreachable from LAN | Firewall or wrong IP | `sudo ufw allow 8000/tcp`; check `hostname -I` |
| `/health` shows `database: error` | Postgres down or credentials | `./scripts/stack.sh ps`; check db logs |
| `redis: error` | Redis not running | `docker compose -f docker-compose.prod.yml logs redis` |
| Jobs stay queued | Worker not running | `./scripts/stack.sh ps`; start worker; check logs |
| Schedules not firing | Scheduler not running | `./scripts/stack.sh ps`; check scheduler logs |
| 500 on startup | Migrations not applied | `./scripts/stack.sh migrate` |
| Export download 404 | Missing volume data | Confirm `leadfinder_app_data` mounted on app + worker |
| `POSTGRES_PASSWORD` error on up | Missing in `.env` | Set in `.env` before `stack.sh up` |

### App up but DB down

Readiness fails; app may return errors. Fix Postgres first, then `docker compose -f docker-compose.prod.yml restart app`.

### Worker not processing

1. Confirm Redis healthy: `curl localhost:8000/health`
2. Check queue: `curl localhost:8000/api/background/queue`
3. Follow worker logs: `./scripts/stack.sh logs-worker`

---

## Development vs production

| | Development | Production (LAN) |
|---|-------------|------------------|
| Compose file | `docker-compose.yml` | `docker-compose.prod.yml` |
| Source mount | Yes (hot reload) | No (built image) |
| Uvicorn | `--reload` | Multi-worker optional, no reload |
| Restart policy | None | `unless-stopped` |
| DB/Redis ports | Exposed on all interfaces | Localhost only |
| Migrations | App entrypoint | Dedicated `migrate` service |

Development:

```bash
docker compose up --build
```

Production:

```bash
./scripts/stack.sh up
```

---

## Security notes (LAN-only)

- Do **not** port-forward 8000 on your router to the internet.
- Keep Postgres/Redis bound to localhost (default in prod Compose).
- Use a strong `SECRET_KEY` and `POSTGRES_PASSWORD`.
- HTTPS is optional for internal LAN; document internal CA or self-signed cert separately if needed later.

---

## File reference

| Path | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production stack |
| `docker-compose.yml` | Development stack |
| `Dockerfile` | Application image |
| `scripts/entrypoint-*.sh` | Service startup |
| `scripts/wait_for_dependencies.py` | DB/Redis wait |
| `scripts/stack.sh` | Operational helper |
| `deploy/nginx/leadfinder.conf` | Internal reverse proxy |
| `deploy/systemd/leadfinder.service` | Boot-time Compose unit |
| `.env.example` | Configuration template |
