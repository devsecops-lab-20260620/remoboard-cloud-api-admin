"""Unit tests — 503 Service Unavailable when DB is unreachable."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig
from app.database import get_db
from app.dependencies import get_config
from app.main import create_fastapi_app


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        admin_auth_username="test-admin",
        admin_auth_password="test-pass",
        admin_auth_jwt_secret="test-secret",
        admin_auth_access_token_ttl_seconds=60,
        admin_auth_refresh_token_ttl_seconds=120,
        admin_auth_issuer="test-issuer",
    )


@pytest.fixture
def client_with_broken_db(config: AppConfig) -> Generator[TestClient, None, None]:
    """TestClient where DB session raises on any query."""
    app = create_fastapi_app(config=config)
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("connection refused")

    app.dependency_overrides[get_config] = lambda: config
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestDbUnavailable503:
    def test_me_returns_503_when_db_down(self, client_with_broken_db: TestClient, config: AppConfig) -> None:
        # Login succeeds (no DB needed for login)
        res = client_with_broken_db.post(
            "/api/admin/auth/login",
            json={"username": "test-admin", "password": "test-pass"},
        )
        assert res.status_code == 200
        token = res.json()["access_token"]

        # /me requires DB for revoke check → 503
        res = client_with_broken_db.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 503
        assert res.json()["detail"] == "Service temporarily unavailable"

    def test_logout_returns_503_when_db_down(self, client_with_broken_db: TestClient) -> None:
        res = client_with_broken_db.post(
            "/api/admin/auth/login",
            json={"username": "test-admin", "password": "test-pass"},
        )
        token = res.json()["access_token"]

        res = client_with_broken_db.post(
            "/api/admin/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 503

    def test_login_succeeds_even_when_db_down(self, client_with_broken_db: TestClient) -> None:
        res = client_with_broken_db.post(
            "/api/admin/auth/login",
            json={"username": "test-admin", "password": "test-pass"},
        )
        assert res.status_code == 200
        assert "access_token" in res.json()
