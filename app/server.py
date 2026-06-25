from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .auth import AdminAuthService, AuthenticationError, InvalidCredentialsError, InvalidTokenError, TokenRevokedError
from .config import AppConfig


JsonDict = Dict[str, Any]
StartResponse = Callable[[str, List[Tuple[str, str]]], None]


@dataclass
class HttpError(Exception):
    status: str
    message: str
    details: Optional[Any] = None


@dataclass
class HttpResponse:
    status: str
    body: bytes
    headers: List[Tuple[str, str]]


class AdminApiApp:
    def __init__(self, config: Optional[AppConfig] = None, auth_service: Optional[AdminAuthService] = None):
        self.config = config or AppConfig.from_env()
        self.auth_service = auth_service or AdminAuthService(self.config)

    def __call__(self, environ: Dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        response = self.handle_request(environ)
        start_response(response.status, response.headers)
        return [response.body]

    def handle_request(self, environ: Dict[str, Any]) -> HttpResponse:
        method = (environ.get("REQUEST_METHOD") or "GET").upper()
        path = self._normalize_path(environ.get("PATH_INFO") or "/")

        try:
            if method == "OPTIONS":
                return self._empty_response()
            if method == "GET" and path == "/health":
                return self._json_response({"status": "ok"})
            if method == "POST" and path == "/admin/auth/login":
                return self._login(environ)
            if method == "GET" and path == "/admin/auth/me":
                return self._me(environ)
            if method == "POST" and path == "/admin/auth/refresh":
                return self._refresh(environ)
            if method == "POST" and path == "/admin/auth/logout":
                return self._logout(environ)
            if method == "GET" and path == "/":
                return self._json_response({"service": "remoboard-cloud-api-admin", "status": "running"})
            raise HttpError(status="404 Not Found", message="Not Found")
        except HttpError as exc:
            return self._error_response(exc)
        except InvalidCredentialsError as exc:
            return self._error_response(HttpError(status="401 Unauthorized", message=str(exc)))
        except (InvalidTokenError, TokenRevokedError) as exc:
            return self._error_response(HttpError(status="401 Unauthorized", message=str(exc)))
        except AuthenticationError as exc:
            return self._error_response(HttpError(status="401 Unauthorized", message=str(exc)))
        except ValueError as exc:
            return self._error_response(HttpError(status="400 Bad Request", message=str(exc)))
        except Exception as exc:  # pragma: no cover - defensive fallback
            return self._error_response(HttpError(status="500 Internal Server Error", message="Internal Server Error", details=str(exc)))

    def _login(self, environ: Dict[str, Any]) -> HttpResponse:
        payload = self._read_json_body(environ)
        username = payload.get("username")
        password = payload.get("password")
        if not username or not password:
            raise HttpError(status="400 Bad Request", message="username and password are required")
        profile = self.auth_service.authenticate(username=username, password=password)
        token_pair = self.auth_service.issue_token_pair(profile)
        return self._json_response(
            {
                "token_type": "bearer",
                "access_token": token_pair.access_token,
                "refresh_token": token_pair.refresh_token,
                "expires_in": token_pair.access_expires_in,
                "refresh_expires_in": token_pair.refresh_expires_in,
                "admin": profile.to_dict(),
            },
            status="200 OK",
        )

    def _me(self, environ: Dict[str, Any]) -> HttpResponse:
        claims = self._require_bearer_token(environ)
        return self._json_response(
            {
                "admin": {
                    "username": claims["sub"],
                    "display_name": claims.get("display_name", self.config.admin_display_name),
                    "roles": claims.get("roles", ["admin"]),
                }
            }
        )

    def _refresh(self, environ: Dict[str, Any]) -> HttpResponse:
        payload = self._read_json_body(environ)
        refresh_token = payload.get("refresh_token")
        if not refresh_token:
            raise HttpError(status="400 Bad Request", message="refresh_token is required")
        token_pair = self.auth_service.refresh_tokens(refresh_token)
        return self._json_response(
            {
                "token_type": "bearer",
                "access_token": token_pair.access_token,
                "refresh_token": token_pair.refresh_token,
                "expires_in": token_pair.access_expires_in,
                "refresh_expires_in": token_pair.refresh_expires_in,
            }
        )

    def _logout(self, environ: Dict[str, Any]) -> HttpResponse:
        token = self._extract_bearer_token(environ)
        if token:
            self.auth_service.revoke_token(token)
        return self._json_response({"status": "logged_out"})

    def _require_bearer_token(self, environ: Dict[str, Any]) -> JsonDict:
        token = self._extract_bearer_token(environ)
        if not token:
            raise HttpError(status="401 Unauthorized", message="Missing bearer token")
        return self.auth_service.verify_access_token(token)

    def _extract_bearer_token(self, environ: Dict[str, Any]) -> Optional[str]:
        header = environ.get("HTTP_AUTHORIZATION") or ""
        if not header.lower().startswith("bearer "):
            return None
        return header[7:].strip() or None

    def _read_json_body(self, environ: Dict[str, Any]) -> JsonDict:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ.get("wsgi.input").read(content_length) if content_length else b""
        if not body:
            return {}
        try:
            decoded = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HttpError(status="400 Bad Request", message="Request body must be UTF-8 encoded") from exc
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise HttpError(status="400 Bad Request", message="Invalid JSON body") from exc
        if not isinstance(data, dict):
            raise HttpError(status="400 Bad Request", message="JSON body must be an object")
        return data

    def _json_response(self, payload: JsonDict, status: str = "200 OK", extra_headers: Optional[List[Tuple[str, str]]] = None) -> HttpResponse:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ]
        if extra_headers:
            headers.extend(extra_headers)
        return HttpResponse(status=status, body=body, headers=headers)

    def _error_response(self, error: HttpError) -> HttpResponse:
        payload: JsonDict = {"error": error.message}
        if error.details is not None:
            payload["details"] = error.details
        return self._json_response(payload, status=error.status)

    def _empty_response(self) -> HttpResponse:
        return HttpResponse(
            status="204 No Content",
            body=b"",
            headers=[
                ("Content-Length", "0"),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ],
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        if path.startswith("/api"):
            path = path[4:] or "/"
        return path if path.startswith("/") else f"/{path}"


def create_app(config: Optional[AppConfig] = None) -> AdminApiApp:
    return AdminApiApp(config=config)


