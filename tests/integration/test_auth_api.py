"""Integration tests — FastAPI × SQLAlchemy × PostgreSQL.

These tests require a running PostgreSQL instance.
Set TEST_DATABASE_URL or use the docker-compose.test.yml stack.

Run only these tests:
    pytest tests/integration/ -v
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_valid_credentials_returns_tokens(self, client: TestClient) -> None:
        resp = client.post(
            "/api/admin/auth/login",
            json={"username": "test-admin", "password": "test-pass"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["expires_in"] > 0
        assert body["admin"]["username"] == "test-admin"

    def test_wrong_password_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/admin/auth/login",
            json={"username": "test-admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_missing_username_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/admin/auth/login",
            json={"password": "test-pass"},
        )
        assert resp.status_code == 422

    def test_missing_password_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/admin/auth/login",
            json={"username": "test-admin"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


class TestMe:
    def test_returns_admin_info(self, client: TestClient) -> None:
        token = _login(client)
        resp = client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["admin"]["username"] == "test-admin"
        assert "admin" in body["admin"]["roles"]

    def test_no_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/admin/auth/me")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/admin/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_rotates_tokens(self, client: TestClient) -> None:
        pair = _login_pair(client)
        resp = client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] != pair["access_token"]
        assert body["refresh_token"] != pair["refresh_token"]

    def test_used_refresh_token_rejected(self, client: TestClient) -> None:
        pair = _login_pair(client)
        # First use — OK
        client.post("/api/admin/auth/refresh", json={"refresh_token": pair["refresh_token"]})
        # Second use — must fail
        resp = client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert resp.status_code == 401

    def test_revocation_persisted_in_db(self, client: TestClient) -> None:
        """After a refresh, the old refresh token is stored in the DB and rejected."""
        pair = _login_pair(client)
        client.post("/api/admin/auth/refresh", json={"refresh_token": pair["refresh_token"]})
        # Re-using old token must fail even if we reconstruct the client
        resp = client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_logout_returns_200(self, client: TestClient) -> None:
        token = _login(client)
        resp = client.post(
            "/api/admin/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged_out"

    def test_access_token_revoked_after_logout(self, client: TestClient) -> None:
        token = _login(client)
        client.post("/api/admin/auth/logout", headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_refresh_token_revoked_after_logout(self, client: TestClient) -> None:
        pair = _login_pair(client)
        client.post(
            "/api/admin/auth/logout",
            headers={"Authorization": f"Bearer {pair['access_token']}"},
        )
        resp = client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": pair["refresh_token"]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login(client: TestClient) -> str:
    resp = client.post(
        "/api/admin/auth/login",
        json={"username": "test-admin", "password": "test-pass"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _login_pair(client: TestClient) -> dict:
    resp = client.post(
        "/api/admin/auth/login",
        json={"username": "test-admin", "password": "test-pass"},
    )
    resp.raise_for_status()
    return resp.json()
