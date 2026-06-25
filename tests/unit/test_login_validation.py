"""Unit tests — login endpoint validation (no DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestLoginValidation:
    def test_username_only_without_password_returns_422(self, client_no_db: TestClient) -> None:
        res = client_no_db.post("/api/admin/auth/login", json={"username": "admin"})
        assert res.status_code == 422

    def test_password_only_without_username_returns_422(self, client_no_db: TestClient) -> None:
        res = client_no_db.post("/api/admin/auth/login", json={"password": "secret"})
        assert res.status_code == 422

    def test_empty_password_returns_422(self, client_no_db: TestClient) -> None:
        res = client_no_db.post("/api/admin/auth/login", json={"username": "admin", "password": ""})
        assert res.status_code == 422

    def test_empty_body_returns_422(self, client_no_db: TestClient) -> None:
        res = client_no_db.post("/api/admin/auth/login", json={})
        assert res.status_code == 422

    def test_too_long_password_returns_422(self, client_no_db: TestClient) -> None:
        res = client_no_db.post("/api/admin/auth/login", json={"username": "admin", "password": "a" * 129})
        assert res.status_code == 422
