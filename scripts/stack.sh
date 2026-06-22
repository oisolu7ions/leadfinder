#!/bin/sh
# Operational helper for the LAN production stack.
# Usage: ./scripts/stack.sh <command>
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE="docker compose -f ${COMPOSE_FILE}"

usage() {
  cat <<EOF
Leadfinder stack helper (LAN production)

Usage: ./scripts/stack.sh <command>

Commands:
  up          Build and start all services (detached)
  down        Stop all services
  restart     Restart app, worker, and scheduler
  ps          Show service status
  logs        Follow all service logs
  logs-app    Follow web app logs
  logs-worker Follow worker logs
  logs-sched  Follow scheduler logs
  migrate     Run Alembic migrations
  health      Check /health and /health/ready on localhost:8000
  backup      Backup Postgres + data volume contents
  update      Pull code, rebuild, migrate, restart (run from repo root)
  proxy-up    Start stack with internal Nginx on port 80
  proxy-down  Stop stack including Nginx profile

Environment:
  COMPOSE_FILE   Compose file (default: docker-compose.prod.yml)
EOF
}

cmd_up() {
  $COMPOSE up -d --build --remove-orphans
  echo "Stack started. LAN access: http://<vm-ip>:8000"
}

cmd_down() {
  $COMPOSE down
}

cmd_restart() {
  $COMPOSE restart app worker scheduler
}

cmd_ps() {
  $COMPOSE ps
}

cmd_logs() {
  $COMPOSE logs -f --tail=200
}

cmd_logs_app() {
  $COMPOSE logs -f --tail=200 app
}

cmd_logs_worker() {
  $COMPOSE logs -f --tail=200 worker
}

cmd_logs_sched() {
  $COMPOSE logs -f --tail=200 scheduler
}

cmd_migrate() {
  $COMPOSE run --rm migrate
}

cmd_health() {
  echo "== /health/live =="
  curl -fsS "http://127.0.0.1:${PORT:-8000}/health/live" && echo
  echo "== /health/ready =="
  curl -fsS "http://127.0.0.1:${PORT:-8000}/health/ready" && echo
  echo "== /health =="
  curl -fsS "http://127.0.0.1:${PORT:-8000}/health" && echo
}

cmd_backup() {
  BACKUP_DIR="${BACKUP_DIR:-${ROOT}/backups}"
  STAMP="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$BACKUP_DIR"
  DUMP="${BACKUP_DIR}/leadfinder_db_${STAMP}.sql"
  echo "Writing database dump to ${DUMP}"
  $COMPOSE exec -T db pg_dump -U "${POSTGRES_USER:-leadfinder}" "${POSTGRES_DB:-leadfinder}" > "$DUMP"
  DATA_ARCHIVE="${BACKUP_DIR}/leadfinder_data_${STAMP}.tar.gz"
  echo "Archiving app data volume to ${DATA_ARCHIVE}"
  docker run --rm \
    -v "leadfinder_app_data:/data:ro" \
    -v "$BACKUP_DIR:/backup" \
    alpine:3.20 \
    tar czf "/backup/$(basename "$DATA_ARCHIVE")" -C /data .
  echo "Backup complete."
}

cmd_update() {
  echo "Pulling latest code..."
  git pull --ff-only
  $COMPOSE build app worker scheduler migrate
  $COMPOSE run --rm migrate
  $COMPOSE up -d app worker scheduler
  cmd_health || true
  echo "Update complete."
}

cmd_proxy_up() {
  $COMPOSE --profile proxy up -d --build --remove-orphans
  echo "Stack with Nginx started. LAN access: http://<vm-ip>/"
}

cmd_proxy_down() {
  $COMPOSE --profile proxy down
}

case "${1:-}" in
  up) cmd_up ;;
  down) cmd_down ;;
  restart) cmd_restart ;;
  ps) cmd_ps ;;
  logs) cmd_logs ;;
  logs-app) cmd_logs_app ;;
  logs-worker) cmd_logs_worker ;;
  logs-sched) cmd_logs_sched ;;
  migrate) cmd_migrate ;;
  health) cmd_health ;;
  backup) cmd_backup ;;
  update) cmd_update ;;
  proxy-up) cmd_proxy_up ;;
  proxy-down) cmd_proxy_down ;;
  *) usage; exit 1 ;;
esac
