"""Shared helpers for server-rendered dashboard routes."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from app import __version__
from app.core.config import Settings, get_settings
from app.services import ui_presenters
from app.utils.csrf import generate_csrf_token

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["tojson"] = lambda value, indent=None: json.dumps(
    value, indent=indent, default=str
)
templates.env.globals["ui"] = ui_presenters


def base_context(request: Request, settings: Settings | None = None) -> dict[str, Any]:
    """Context variables shared by all dashboard templates."""
    settings = settings or get_settings()
    ctx: dict[str, Any] = {
        "request": request,
        "app_name": settings.app_name,
        "version": __version__,
        "csrf_token": generate_csrf_token(settings.secret_key),
    }
    if msg := request.query_params.get("msg"):
        ctx["flash_message"] = msg
    if err := request.query_params.get("err"):
        ctx["flash_error"] = err
    return ctx


def redirect_with_message(url: str, message: str | None = None, error: str | None = None) -> RedirectResponse:
    """Redirect with a flash query parameter."""
    params: list[str] = []
    if message:
        params.append(f"msg={message}")
    if error:
        params.append(f"err={error}")
    if params:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{'&'.join(params)}"
    return RedirectResponse(url=url, status_code=303)
