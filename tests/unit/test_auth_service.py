"""Unit tests — AdminAuthService (no DB, no HTTP layer)."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.auth import (
    AdminAuthService,
    AdminProfile,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenRevokedError,
)
from app.config import AppConfig


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        admin_auth_username="unit-admin",
        admin_auth_password="unit-pass",
        admin_auth_display_name="Unit Admin",
        admin_auth_jwt_secret="unit-secret",
        admin_auth_access_token_ttl_seconds=60,
        admin_auth_refresh_token_ttl_seconds=120,
        admin_auth_issuer="unit-test-issuer",
    )


@pytest.fixture
def svc(config: AppConfig) -> AdminAuthService:
    """Auth service with NO database (in-memory blacklist)."""
    return AdminAuthService(config=config, db=None)


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------


class TestAuthenticate:
    def test_valid_credentials_return_profile(self, svc: AdminAuthService) -> None:
        profile = svc.authenticate("unit-admin", "unit-pass")
        assert profile.username == "unit-admin"
        assert profile.display_name == "Unit Admin"
        assert "admin" in profile.roles

    def test_wrong_password_raises(self, svc: AdminAuthService) -> None:
        with pytest.raises(InvalidCredentialsError):
            svc.authenticate("unit-admin", "wrong")

    def test_wrong_username_raises(self, svc: AdminAuthService) -> None:
        with pytest.raises(InvalidCredentialsError):
            svc.authenticate("other", "unit-pass")

    def test_empty_credentials_raises(self, svc: AdminAuthService) -> None:
        with pytest.raises(InvalidCredentialsError):
            svc.authenticate("", "")


# ---------------------------------------------------------------------------
# issue_token_pair
# ---------------------------------------------------------------------------


class TestIssueTokenPair:
    def test_returns_two_tokens(self, svc: AdminAuthService, config: AppConfig) -> None:
        profile = svc.admin_profile
        pair = svc.issue_token_pair(profile)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.access_token != pair.refresh_token

    def test_access_token_expires_in_is_positive(
        self, svc: AdminAuthService
    ) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        assert 0 < pair.access_expires_in <= 60

    def test_same_session_id_in_both_tokens(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        access_claims = svc.verify_token(pair.access_token)
        refresh_claims = svc.verify_token(pair.refresh_token)
        assert access_claims["sid"] == refresh_claims["sid"]


# ---------------------------------------------------------------------------
# verify_token / verify_access_token
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def test_valid_access_token_returns_claims(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        claims = svc.verify_access_token(pair.access_token)
        assert claims["sub"] == "unit-admin"
        assert claims["typ"] == "access"

    def test_wrong_token_type_rejected(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        with pytest.raises(InvalidTokenError):
            svc.verify_token(pair.refresh_token, expected_type="access")

    def test_tampered_signature_rejected(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        tampered = pair.access_token[:-4] + "XXXX"
        with pytest.raises(InvalidTokenError):
            svc.verify_access_token(tampered)

    def test_malformed_token_rejected(self, svc: AdminAuthService) -> None:
        with pytest.raises(InvalidTokenError):
            svc.verify_access_token("not.a.jwt")

    def test_expired_token_rejected(self, config: AppConfig) -> None:
        # Create a service with 0-second TTL
        zero_ttl_config = AppConfig(
            admin_auth_username=config.admin_username,
            admin_auth_password=config.admin_password,
            admin_auth_jwt_secret=config.jwt_secret,
            admin_auth_access_token_ttl_seconds=0,
            admin_auth_refresh_token_ttl_seconds=0,
            admin_auth_issuer=config.issuer,
        )
        zero_svc = AdminAuthService(config=zero_ttl_config, db=None)
        pair = zero_svc.issue_token_pair(zero_svc.admin_profile)
        # Should be expired immediately
        with pytest.raises(InvalidTokenError, match="expired"):
            zero_svc.verify_access_token(pair.access_token)

    def test_wrong_issuer_rejected(self, svc: AdminAuthService, config: AppConfig) -> None:
        """A token from a different issuer must not be accepted."""
        other_config = AppConfig(
            admin_auth_username=config.admin_username,
            admin_auth_password=config.admin_password,
            admin_auth_jwt_secret=config.jwt_secret,
            admin_auth_issuer="evil-issuer",
        )
        other_svc = AdminAuthService(config=other_config, db=None)
        pair = other_svc.issue_token_pair(other_svc.admin_profile)
        with pytest.raises(InvalidTokenError, match="issuer"):
            svc.verify_access_token(pair.access_token)


# ---------------------------------------------------------------------------
# revoke_token / refresh_tokens (in-memory)
# ---------------------------------------------------------------------------


class TestRevocation:
    def test_revoked_jti_rejected(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        svc.revoke_token(pair.access_token)
        with pytest.raises(TokenRevokedError):
            svc.verify_access_token(pair.access_token)

    def test_logout_revokes_session(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        # Revoke via the access token (logout path)
        svc.revoke_token(pair.access_token)
        # Refresh token shares the same session — must also be rejected
        with pytest.raises(TokenRevokedError):
            svc.verify_token(pair.refresh_token)

    def test_refresh_rotates_tokens(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        new_pair = svc.refresh_tokens(pair.refresh_token)
        assert new_pair.access_token != pair.access_token
        assert new_pair.refresh_token != pair.refresh_token

    def test_used_refresh_token_rejected(self, svc: AdminAuthService) -> None:
        pair = svc.issue_token_pair(svc.admin_profile)
        svc.refresh_tokens(pair.refresh_token)
        with pytest.raises(TokenRevokedError):
            svc.refresh_tokens(pair.refresh_token)

