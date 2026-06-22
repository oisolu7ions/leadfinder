"""Database session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(settings: Settings | None = None):
    """Return a singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = settings or get_settings()
        _engine = create_engine(
            settings.sqlalchemy_database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Return a singleton session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(settings),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_engine() -> None:
    """Reset engine and session factory — used in tests."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
