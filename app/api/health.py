"""Health check API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.db.redis import ping_redis
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Return application and dependency health status."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "ok" if ping_redis() else "error"
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        app_name=settings.app_name,
        version=__version__,
        database=db_status,
        redis=redis_status,
    )


@router.get("/health/live")
def liveness() -> dict[str, str]:
    """Kubernetes-style liveness probe — process is running."""
    return {"status": "alive"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness probe — dependencies are reachable."""
    try:
        db.execute(text("SELECT 1"))
        redis_ok = ping_redis()
    except Exception:
        return {"status": "not_ready"}

    if redis_ok:
        return {"status": "ready"}
    return {"status": "not_ready"}
