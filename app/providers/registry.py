"""Provider registry — resolve provider implementations by name."""

from __future__ import annotations

from app.core.logging import get_logger
from app.providers.base import BaseProvider
from app.providers.mock import MockProvider

logger = get_logger(__name__)

_REGISTRY: dict[str, BaseProvider] | None = None


def reset_provider_registry() -> None:
    """Clear cached providers (tests / settings reload)."""
    global _REGISTRY
    _REGISTRY = None


def _build_registry() -> dict[str, BaseProvider]:
    from app.core.config import get_settings

    providers: dict[str, BaseProvider] = {MockProvider.name: MockProvider()}
    settings = get_settings()

    if settings.tomtom_enabled:
        if settings.tomtom_api_key:
            from app.providers.tomtom import TomTomProvider

            providers[TomTomProvider.name] = TomTomProvider(settings)
        else:
            logger.warning(
                "tomtom_enabled_missing_api_key",
                hint="Set TOMTOM_API_KEY or disable TOMTOM_ENABLED",
            )

    return providers


def _registry() -> dict[str, BaseProvider]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def get_provider(name: str) -> BaseProvider:
    """Return a provider instance by name."""
    provider = _registry().get(name)
    if provider is None:
        known = ", ".join(sorted(_registry()))
        raise ValueError(f"Unknown provider: {name!r}. Available: {known}")
    return provider


def list_providers() -> list[BaseProvider]:
    """Return all registered providers."""
    return list(_registry().values())


def list_provider_summaries() -> list[dict]:
    """Provider metadata for UI/API (no secrets)."""
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "is_live": p.is_live,
            "default_scan_limit": p.default_scan_limit,
            "max_scan_limit": p.max_scan_limit,
        }
        for p in list_providers()
    ]
