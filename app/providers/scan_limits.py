"""Scan limit helpers for live vs mock providers."""

from __future__ import annotations

from app.providers.registry import get_provider


def effective_scan_limit(source_name: str, requested_limit: int) -> int:
    """Cap scan batch size based on provider capabilities."""
    provider = get_provider(source_name)
    cap = provider.max_scan_limit
    return min(max(1, requested_limit), cap)


def is_live_provider(source_name: str) -> bool:
    return get_provider(source_name).is_live
