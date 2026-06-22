#!/usr/bin/env python3
"""Block until Postgres and Redis are reachable (container startup helper)."""

from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def wait_for_postgres(database_url: str, timeout_seconds: int, interval: float) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("postgres_ready")
            return
        except OperationalError as exc:
            print(f"waiting_for_postgres: {exc}", file=sys.stderr)
            time.sleep(interval)
    print("postgres_wait_timeout", file=sys.stderr)
    sys.exit(1)


def wait_for_redis(redis_url: str, timeout_seconds: int, interval: float) -> None:
    if redis is None:
        print("redis_client_unavailable", file=sys.stderr)
        sys.exit(1)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            client = redis.from_url(redis_url, socket_connect_timeout=2)
            if client.ping():
                print("redis_ready")
                return
        except Exception as exc:
            print(f"waiting_for_redis: {exc}", file=sys.stderr)
            time.sleep(interval)
    print("redis_wait_timeout", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    database_url = _env("DATABASE_URL")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    timeout = int(os.environ.get("STARTUP_WAIT_SECONDS", "120"))
    interval = float(os.environ.get("STARTUP_WAIT_INTERVAL", "2"))

    wait_for_postgres(database_url, timeout, interval)
    wait_for_redis(redis_url, timeout, interval)


if __name__ == "__main__":
    main()
