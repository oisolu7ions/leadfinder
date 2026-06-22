"""Tests for application configuration."""

from app.core.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "leadfinder"
    assert settings.worker_concurrency == 2
    assert settings.inspection_browser_enabled is False


def test_get_settings_cached() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
