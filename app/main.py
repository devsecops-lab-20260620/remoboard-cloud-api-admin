"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import AppConfig
from .database import init_db
from .routers import auth as auth_router
from .routers import health as health_router


def create_fastapi_app(config: AppConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Optional pre-built config (useful in tests to avoid reading
                ``.env`` from disk).
    """
    cfg = config or AppConfig()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Initialise the DB connection pool on startup
        init_db(cfg.database_url)
        yield
        # (pool is released automatically by SQLAlchemy GC)

    app = FastAPI(
        title="remoboard-cloud-api-admin",
        version="0.1.0",
        description="Administration API for Remoboard Cloud",
        lifespan=lifespan,
    )

    # Store config on app state so routers/middleware can access it
    app.state.config = cfg

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router.router)
    app.include_router(auth_router.router, prefix="/api/admin/auth")

    return app


# Module-level app instance (used by uvicorn)
app = create_fastapi_app()
