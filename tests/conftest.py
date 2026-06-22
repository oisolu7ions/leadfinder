"""Pytest configuration and shared fixtures."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _load_dotenv() -> None:
    """Load .env into os.environ without overriding existing values."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def client() -> TestClient:
    """HTTP client for API integration tests."""
    from app.core.config import get_settings
    from app.db.session import reset_engine
    from app.main import app
    from app.providers.registry import reset_provider_registry

    get_settings.cache_clear()
    reset_provider_registry()
    reset_engine()

    return TestClient(app)
