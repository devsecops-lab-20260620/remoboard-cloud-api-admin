from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
import secrets
import threading
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from .config import AppConfig

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AuthenticationError(Exception):
    pass


class InvalidTokenError(AuthenticationError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class TokenRevokedError(AuthenticationError):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int


@dataclass(frozen=True)
class AdminProfile:
    username: str
    display_name: str
    roles: Tuple[str, ...] = ("admin",)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "roles": list(self.roles),
        }


class AdminAuthService:
    """JWT-based authentication service.

    When *db* is provided (production / integration tests), token revocation
    is persisted in PostgreSQL so it survives restarts.
    When *db* is ``None`` (unit tests), an in-memory blacklist is used.
    """

    def __init__(self, config: AppConfig, db: "Optional[Session]" = None):
        self._config = config
        self._db = db
        # ── in-memory fallback (used when db is None) ──────────────────
        self._revoked_jti: Dict[str, int] = {}
        self._revoked_sid: Dict[str, int] = {}
        self._lock = threading.RLock()

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def admin_profile(self) -> AdminProfile:
        return AdminProfile(
            username=self._config.admin_username,
            display_name=self._config.admin_display_name,
        )

    def authenticate(self, username: str, password: str) -> AdminProfile:
        if not (
            secrets.compare_digest(username or "", self._config.admin_username)
            and secrets.compare_digest(password or "", self._config.admin_password)
        ):
            raise InvalidCredentialsError("Invalid administrator credentials")
        return self.admin_profile

    def issue_token_pair(self, profile: AdminProfile, session_id: Optional[str] = None) -> TokenPair:
        session_id = session_id or uuid.uuid4().hex
        now = self._now()
        session_expires_at = now + self._config.refresh_token_ttl_seconds
        access_token, access_claims = self._create_token(
            profile,
            "access",
            now=now,
            ttl_seconds=self._config.access_token_ttl_seconds,
            session_id=session_id,
            session_expires_at=session_expires_at,
        )
        refresh_token, refresh_claims = self._create_token(
            profile,
            "refresh",
            now=now,
            ttl_seconds=self._config.refresh_token_ttl_seconds,
            session_id=session_id,
            session_expires_at=session_expires_at,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=self._seconds_until(access_claims["exp"]),
            refresh_expires_in=self._seconds_until(refresh_claims["exp"]),
        )

    def refresh_tokens(self, refresh_token: str) -> TokenPair:
        claims = self.verify_token(refresh_token, expected_type="refresh")
        self.revoke_jti(claims["jti"], claims["exp"])
        profile = AdminProfile(
            username=claims["sub"],
            display_name=claims.get("display_name", self._config.admin_display_name),
            roles=tuple(claims.get("roles", ["admin"])),
        )
        return self.issue_token_pair(profile, session_id=claims.get("sid"))

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        return self.verify_token(token, expected_type="access")

    def verify_token(self, token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
        claims = self._decode_jwt(token)
        self._validate_claims(claims, expected_type=expected_type)
        jti = claims.get("jti")
        sid = claims.get("sid")
        if jti and self.is_revoked(jti):
            raise TokenRevokedError("Token has been revoked")
        if sid and self.is_session_revoked(sid):
            raise TokenRevokedError("Session has been revoked")
        return claims

    def revoke_token(self, token: str) -> None:
        claims = self._decode_jwt(token)
        jti = claims.get("jti")
        exp = claims.get("exp")
        sid = claims.get("sid")
        session_exp = claims.get("session_exp", exp)
        if jti and exp:
            self.revoke_jti(jti, int(exp))
        if sid and session_exp:
            self.revoke_session(sid, int(session_exp))

    # ── Revocation helpers ───────────────────────────────────────────────

    def revoke_jti(self, jti: str, exp: int) -> None:
        if self._db is not None:
            self._db_revoke_jti(jti, exp)
        else:
            with self._lock:
                self._purge_locked()
                self._revoked_jti[jti] = exp

    def revoke_session(self, sid: str, exp: int) -> None:
        if self._db is not None:
            self._db_revoke_session(sid, exp)
        else:
            with self._lock:
                self._purge_locked()
                self._revoked_sid[sid] = max(exp, self._revoked_sid.get(sid, 0))

    def is_revoked(self, jti: str) -> bool:
        if self._db is not None:
            return self._db_is_jti_revoked(jti)
        with self._lock:
            self._purge_locked()
            return jti in self._revoked_jti

    def is_session_revoked(self, sid: str) -> bool:
        if self._db is not None:
            return self._db_is_session_revoked(sid)
        with self._lock:
            self._purge_locked()
            return sid in self._revoked_sid

    # ── DB-backed revocation (imported lazily to decouple from models) ───

    def _db_revoke_jti(self, jti: str, exp: int) -> None:
        assert self._db is not None
        existing = self._db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if not existing:
            self._db.add(RevokedToken(jti=jti, expires_at=datetime.fromtimestamp(exp, tz=timezone.utc)))
            self._db.commit()

    def _db_revoke_session(self, sid: str, exp: int) -> None:
        assert self._db is not None
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        existing = self._db.query(RevokedSession).filter(RevokedSession.sid == sid).first()
        if existing:
            if expires_at > existing.expires_at:
                existing.expires_at = expires_at
                self._db.commit()
        else:
            self._db.add(RevokedSession(sid=sid, expires_at=expires_at))
            self._db.commit()

    def _db_is_jti_revoked(self, jti: str) -> bool:
        assert self._db is not None
        now = datetime.now(timezone.utc)
        return (
            self._db.query(RevokedToken)
            .filter(RevokedToken.jti == jti, RevokedToken.expires_at > now)
            .first()
        ) is not None

    def _db_is_session_revoked(self, sid: str) -> bool:
        assert self._db is not None
        now = datetime.now(timezone.utc)
        return (
            self._db.query(RevokedSession)
            .filter(RevokedSession.sid == sid, RevokedSession.expires_at > now)
            .first()
        ) is not None

    # ── JWT core ─────────────────────────────────────────────────────────

    def _create_token(
        self,
        profile: AdminProfile,
        token_type: str,
        now: int,
        ttl_seconds: int,
        session_id: str,
        session_expires_at: int,
    ) -> Tuple[str, Dict[str, Any]]:
        exp = now + ttl_seconds
        claims: Dict[str, Any] = {
            "iss": self._config.issuer,
            "sub": profile.username,
            "typ": token_type,
            "iat": now,
            "nbf": now,
            "exp": exp,
            "jti": uuid.uuid4().hex,
            "sid": session_id,
            "session_exp": session_expires_at,
            "display_name": profile.display_name,
            "roles": list(profile.roles),
        }
        return self._encode_jwt(claims), claims

    def _decode_jwt(self, token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise InvalidTokenError("Malformed token")
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_signature = hmac.new(
            self._config.jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_signature = self._urlsafe_b64decode(signature_b64)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise InvalidTokenError("Invalid token signature")
        payload_bytes = self._urlsafe_b64decode(payload_b64)
        try:
            claims = json.loads(payload_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise InvalidTokenError("Invalid token payload") from exc
        if not isinstance(claims, dict):
            raise InvalidTokenError("Invalid token payload")
        return claims

    def _validate_claims(self, claims: Dict[str, Any], expected_type: Optional[str]) -> None:
        required = ("iss", "sub", "typ", "iat", "nbf", "exp", "jti", "sid", "session_exp")
        missing = [field for field in required if field not in claims]
        if missing:
            raise InvalidTokenError(f"Missing claims: {', '.join(missing)}")
        if claims["iss"] != self._config.issuer:
            raise InvalidTokenError("Invalid token issuer")
        if expected_type and claims["typ"] != expected_type:
            raise InvalidTokenError("Unexpected token type")
        now = self._now()
        if int(claims["nbf"]) > now:
            raise InvalidTokenError("Token is not yet valid")
        if int(claims["exp"]) <= now:
            raise InvalidTokenError("Token has expired")

    def _encode_jwt(self, claims: Dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self._urlsafe_b64encode(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        payload_b64 = self._urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(
            self._config.jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        signature_b64 = self._urlsafe_b64encode(signature)
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def _purge_locked(self) -> None:
        """Remove expired entries from the in-memory blacklists (call inside lock)."""
        now = self._now()
        expired_jti = [jti for jti, exp in self._revoked_jti.items() if exp <= now]
        for jti in expired_jti:
            self._revoked_jti.pop(jti, None)
        expired_sid = [sid for sid, exp in self._revoked_sid.items() if exp <= now]
        for sid in expired_sid:
            self._revoked_sid.pop(sid, None)

    def _now(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def _seconds_until(self, exp: int) -> int:
        return max(0, int(exp) - self._now())

    @staticmethod
    def _urlsafe_b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    @staticmethod
    def _urlsafe_b64decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)


