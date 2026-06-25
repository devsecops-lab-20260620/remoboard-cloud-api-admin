"""SQLAlchemy engine / session management."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# Declarative base — shared by all models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Module-level singletons (initialised lazily or via init_db)
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal: sessionmaker | None = None  # type: ignore[type-arg]


def init_db(database_url: str) -> None:
    """Initialise (or re-initialise) the SQLAlchemy engine and session factory.

    Call this once at application startup, or from test fixtures to point at
    the test database.
    """
    global _engine, _SessionLocal
    _engine = create_engine(database_url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    If the database has not been initialised (e.g. in unit tests that mock
    this dependency), yields ``None`` so that callers can fall back gracefully.
    """
    if _SessionLocal is None:
        yield None  # type: ignore[misc]
        return
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

