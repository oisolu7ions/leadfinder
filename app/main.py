"""FastAPI application factory and lifespan management."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.background_routes import router as background_api_router
from app.api.health import router as health_router
from app.api.inspection_routes import router as inspection_api_router
from app.api.leads import router as leads_api_router
from app.api.export_routes import router as export_api_router
from app.api.outreach_routes import router as outreach_api_router
from app.api.scoring_routes import router as scoring_api_router
from app.api.scans import router as scans_api_router
from app.api.web import router as web_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory
from app.services.scan import ensure_default_sources

logger = get_logger(__name__)


def ensure_data_dirs(settings: Settings) -> None:
    """Create runtime data directories if they do not exist."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "screenshots").mkdir(exist_ok=True)
    (settings.data_dir / "snapshots").mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    settings = get_settings()
    configure_logging(settings)
    ensure_data_dirs(settings)
    try:
        with get_session_factory(settings)() as db:
            ensure_default_sources(db)
    except Exception:
        logger.warning("default_sources_seed_skipped")
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=__version__,
        env=settings.app_env,
    )
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="OIS Lead Discovery Platform",
        description="Internal lead discovery and review tool for OIS",
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
    )

    static_dir = Path("app/static")
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(health_router)
    app.include_router(scans_api_router)
    app.include_router(leads_api_router)
    app.include_router(inspection_api_router)
    app.include_router(scoring_api_router)
    app.include_router(outreach_api_router)
    app.include_router(export_api_router)
    app.include_router(background_api_router)
    app.include_router(web_router)

    return app


app = create_app()
