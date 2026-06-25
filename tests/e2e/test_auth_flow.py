"""E2E tests — full authentication flow verification.

These tests exercise the complete workflow end-to-end:
  1. Login → issue token pair
  2. Access /me with the access token
  3. Refresh tokens
  4. Logout (revoke session)
  5. Verify all tokens are invalid after logout

Security scenarios (JWT, CORS, permission boundaries) are also covered here.

Run only these tests:
    pytest tests/e2e/ -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Full auth flow
# ---------------------------------------------------------------------------


class TestFullAuthFlow:
    """Golden path: login → use API → refresh → logout → verify locked."""

    def test_complete_session_lifecycle(self, client: TestClient) -> None:
        # ① Login
        login_resp = client.post(
            "/api/admin/auth/login",
            json={"username": "test-admin", "password": "test-pass"},
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # ② Access protected resource
        me_resp = client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["admin"]["username"] == "test-admin"

        # ③ Refresh
        refresh_resp = client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        new_access = new_tokens["access_token"]
        new_refresh = new_tokens["refresh_token"]
        assert new_access != access_token
        assert new_refresh != refresh_token

        # Old refresh token must now be rejected
        old_refresh_resp = client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert old_refresh_resp.status_code == 401

        # ④ Logout using new access token
        logout_resp = client.post(
            "/api/admin/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert logout_resp.status_code == 200

        # ⑤ All tokens in this session must now be invalid
        assert (
            client.get(
                "/api/admin/auth/me",
                headers={"Authorization": f"Bearer {new_access}"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": new_refresh},
            ).status_code
            == 401
        )


# ---------------------------------------------------------------------------
# Security scenarios
# ---------------------------------------------------------------------------


class TestSecurityScenarios:
    def test_expired_token_rejected(self, client: TestClient) -> None:
        # Crafted expired JWT (typ=access, exp in the past)
        # Uses a known-bad token — must be rejected without crashing
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiJhZG1pbiIsImV4cCI6MX0"
            ".invalid"
        )
        resp = client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_tampered_signature_rejected(self, client: TestClient) -> None:
        tokens = _login(client)
        tampered = tokens["access_token"][:-4] + "XXXX"
        resp = client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 401

    def test_refresh_token_cannot_be_used_as_access_token(
        self, client: TestClient
    ) -> None:
        tokens = _login(client)
        resp = client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        )
        assert resp.status_code == 401

    def test_brute_force_returns_401_not_500(self, client: TestClient) -> None:
        for _ in range(5):
            resp = client.post(
                "/api/admin/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            assert resp.status_code == 401

    def test_sql_injection_in_credentials_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/admin/auth/login",
            json={"username": "' OR '1'='1", "password": "' OR '1'='1"},
        )
        assert resp.status_code == 401

    def test_missing_bearer_prefix_returns_401(self, client: TestClient) -> None:
        tokens = _login(client)
        resp = client.get(
            "/api/admin/auth/me",
            headers={"Authorization": tokens["access_token"]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------


class TestCorsHeaders:
    def test_cors_header_present(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.headers.get("access-control-allow-origin") == "*"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login(client: TestClient) -> dict:
    resp = client.post(
        "/api/admin/auth/login",
        json={"username": "test-admin", "password": "test-pass"},
    )
    resp.raise_for_status()
    return resp.json()

