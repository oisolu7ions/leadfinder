"""Stateless CSRF token helpers for form submissions."""

import hashlib
import hmac
import time


def generate_csrf_token(secret_key: str, ttl_seconds: int = 3600) -> str:
    """Create a signed CSRF token valid for ``ttl_seconds``."""
    expires = int(time.time()) + ttl_seconds
    payload = str(expires)
    signature = hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def validate_csrf_token(secret_key: str, token: str | None) -> bool:
    """Validate a CSRF token from a form submission."""
    if not token or "." not in token:
        return False
    expires_str, signature = token.split(".", 1)
    try:
        expires = int(expires_str)
    except ValueError:
        return False
    if expires < int(time.time()):
        return False
    expected = hmac.new(
        secret_key.encode(),
        expires_str.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
