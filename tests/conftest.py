"""Shared pytest fixtures for all test layers."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import AppConfig
from app.database import Base, get_db
from app.dependencies import get_config
from app.main import create_fastapi_app

# ---------------------------------------------------------------------------
# Test configuration fixture (no .env / DB required)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_config() -> AppConfig:
    return AppConfig(
        admin_api_host="127.0.0.1",
        admin_api_port=8000,
        admin_auth_username="test-admin",
        admin_auth_password="test-pass",
        admin_auth_display_name="Test Administrator",
        admin_auth_jwt_secret="test-jwt-secret",
        admin_auth_access_token_ttl_seconds=60,
        admin_auth_refresh_token_ttl_seconds=120,
        admin_auth_issuer="test-issuer",
        db_host="localhost",
        db_port=5432,
        db_name="remoboard_test",
        db_user="remoboard_admin",
        db_password="test-password",
    )


# ---------------------------------------------------------------------------
# Database fixtures (used by integration / e2e tests)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://remoboard_admin:test-password@localhost:5432/remoboard_test",
)


@pytest.fixture(scope="session")
def db_engine(test_config: AppConfig):
    """Create tables once per session, drop them after."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a transactional scope that rolls back after each test."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session: Session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# FastAPI test client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_no_db(test_config: AppConfig) -> Generator[TestClient, None, None]:
    """TestClient with DB dependency replaced by None (unit-style tests)."""
    app = create_fastapi_app(config=test_config)
    app.dependency_overrides[get_config] = lambda: test_config
    app.dependency_overrides[get_db] = lambda: None
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def client(test_config: AppConfig, db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with a real DB session (integration / e2e tests)."""
    app = create_fastapi_app(config=test_config)
    app.dependency_overrides[get_config] = lambda: test_config

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
