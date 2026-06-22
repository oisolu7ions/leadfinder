#!/bin/sh
# Web app: wait for dependencies, apply migrations, start uvicorn.
set -eu

cd /app

echo "entrypoint_app_starting"
python scripts/wait_for_dependencies.py

echo "running_migrations"
alembic upgrade head

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-1}"

if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
  echo "starting_uvicorn_reload"
  exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
fi

echo "starting_uvicorn_production workers=${WORKERS}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
