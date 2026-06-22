#!/bin/sh
# Apply Alembic migrations (host or container).
set -eu

cd "$(dirname "$0")/.."

if [ -f /.dockerenv ]; then
  alembic upgrade head
else
  if command -v docker >/dev/null 2>&1 && [ -f docker-compose.prod.yml ]; then
    docker compose -f docker-compose.prod.yml run --rm migrate
  else
    alembic upgrade head
  fi
fi

echo "migrations_applied"
