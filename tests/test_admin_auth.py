from __future__ import annotations

import io
import json
import unittest
from typing import Any, Dict, List, Optional, Tuple

from app.config import AppConfig
from app.server import create_app


class AdminAuthApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig(
            admin_api_host="127.0.0.1",
            admin_api_port=8000,
            admin_auth_username="admin-user",
            admin_auth_password="admin-pass",
            admin_auth_display_name="Admin User",
            admin_auth_jwt_secret="test-secret",
            admin_auth_access_token_ttl_seconds=60,
            admin_auth_refresh_token_ttl_seconds=120,
            admin_auth_issuer="test-issuer",
        )
        self.app = create_app(self.config)

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, List[Tuple[str, str]], Dict[str, Any]]:
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
        environ: Dict[str, Any] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "wsgi.input": io.BytesIO(payload),
            "CONTENT_LENGTH": str(len(payload)),
            "CONTENT_TYPE": "application/json",
        }
        for key, value in (headers or {}).items():
            environ[f"HTTP_{key.upper().replace('-', '_')}"] = value
        captured: Dict[str, Any] = {}

        def start_response(status: str, response_headers: List[Tuple[str, str]]) -> None:
            captured["status"] = status
            captured["headers"] = response_headers

        body_bytes = b"".join(self.app(environ, start_response))
        return captured["status"], captured["headers"], json.loads(body_bytes.decode("utf-8"))

    def test_health_endpoint(self) -> None:
        status, _, payload = self._request("GET", "/health")
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload, {"status": "ok"})

    def test_login_and_me(self) -> None:
        status, _, payload = self._request("POST", "/api/admin/auth/login", {"username": "admin-user", "password": "admin-pass"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["token_type"], "bearer")
        self.assertIn("access_token", payload)
        self.assertIn("refresh_token", payload)

        status, _, me_payload = self._request("GET", "/admin/auth/me", headers={"Authorization": f"Bearer {payload['access_token']}"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(me_payload["admin"]["username"], "admin-user")
        self.assertEqual(me_payload["admin"]["display_name"], "Admin User")

    def test_login_rejects_bad_credentials(self) -> None:
        status, _, payload = self._request("POST", "/admin/auth/login", {"username": "admin-user", "password": "wrong"})
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn("error", payload)

    def test_refresh_rotates_tokens(self) -> None:
        _, _, login_payload = self._request("POST", "/admin/auth/login", {"username": "admin-user", "password": "admin-pass"})
        old_refresh = login_payload["refresh_token"]
        status, _, refresh_payload = self._request("POST", "/admin/auth/refresh", {"refresh_token": old_refresh})
        self.assertEqual(status, "200 OK")
        self.assertNotEqual(refresh_payload["access_token"], login_payload["access_token"])
        self.assertNotEqual(refresh_payload["refresh_token"], old_refresh)

        status, _, old_refresh_payload = self._request("POST", "/admin/auth/refresh", {"refresh_token": old_refresh})
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn("error", old_refresh_payload)

    def test_logout_revokes_access_token(self) -> None:
        _, _, login_payload = self._request("POST", "/admin/auth/login", {"username": "admin-user", "password": "admin-pass"})
        token = login_payload["access_token"]
        refresh_token = login_payload["refresh_token"]
        status, _, payload = self._request("POST", "/admin/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["status"], "logged_out")

        status, _, me_payload = self._request("GET", "/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn("error", me_payload)

        status, _, refresh_payload = self._request("POST", "/admin/auth/refresh", {"refresh_token": refresh_token})
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn("error", refresh_payload)


if __name__ == "__main__":
    unittest.main()
