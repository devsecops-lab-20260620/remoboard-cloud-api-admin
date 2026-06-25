"""Unit tests — health endpoints (no DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_returns_ok(self, client_no_db: TestClient) -> None:
        res = client_no_db.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_root_returns_service_info(self, client_no_db: TestClient) -> None:
        res = client_no_db.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "remoboard-cloud-api-admin"
        assert data["status"] == "running"
