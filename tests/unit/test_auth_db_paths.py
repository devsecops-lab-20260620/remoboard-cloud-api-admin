"""Unit tests — AdminAuthService DB path with mocked Session."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.auth import AdminAuthService, DatabaseUnavailableError, TokenRevokedError
from app.config import AppConfig


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        admin_auth_username="unit-admin",
        admin_auth_password="unit-pass",
        admin_auth_jwt_secret="unit-secret",
        admin_auth_access_token_ttl_seconds=60,
        admin_auth_refresh_token_ttl_seconds=120,
        admin_auth_issuer="unit-test-issuer",
    )


@pytest.fixture
def mock_db() -> MagicMock:
    """Fake SQLAlchemy Session."""
    return MagicMock()


@pytest.fixture
def svc_with_db(config: AppConfig, mock_db: MagicMock) -> AdminAuthService:
    return AdminAuthService(config=config, db=mock_db)


@pytest.fixture
def svc_no_db(config: AppConfig) -> AdminAuthService:
    return AdminAuthService(config=config, db=None)


# ---------------------------------------------------------------------------
# DB なし — インメモリで動作
# ---------------------------------------------------------------------------


class TestNoDb:
    def test_verify_token_works_without_db(self, svc_no_db: AdminAuthService) -> None:
        pair = svc_no_db.issue_token_pair(svc_no_db.admin_profile)
        claims = svc_no_db.verify_access_token(pair.access_token)
        assert claims["sub"] == "unit-admin"

    def test_revoke_uses_memory(self, svc_no_db: AdminAuthService) -> None:
        pair = svc_no_db.issue_token_pair(svc_no_db.admin_profile)
        svc_no_db.revoke_token(pair.access_token)
        with pytest.raises(TokenRevokedError):
            svc_no_db.verify_access_token(pair.access_token)


# ---------------------------------------------------------------------------
# DB あり正常系 — DB パスを通る
# ---------------------------------------------------------------------------


class TestWithDb:
    def test_verify_token_queries_db(self, svc_with_db: AdminAuthService, mock_db: MagicMock) -> None:
        # DB query returns None (not revoked)
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = None

        pair = svc_with_db.issue_token_pair(svc_with_db.admin_profile)
        claims = svc_with_db.verify_access_token(pair.access_token)

        assert claims["sub"] == "unit-admin"
        assert mock_db.query.called

    def test_revoke_writes_to_db(self, svc_with_db: AdminAuthService, mock_db: MagicMock) -> None:
        # Simulate no existing record
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = None

        pair = svc_with_db.issue_token_pair(svc_with_db.admin_profile)
        svc_with_db.revoke_token(pair.access_token)

        assert mock_db.add.called
        assert mock_db.commit.called


# ---------------------------------------------------------------------------
# DB 例外時 — フォールバックで False を返す（500 にならない）
# ---------------------------------------------------------------------------


class TestDbFailure:
    def test_db_exception_on_revoke_check_raises_database_unavailable(
        self,
        svc_with_db: AdminAuthService,
        mock_db: MagicMock,
    ) -> None:
        # DB query raises an exception (connection lost etc.)
        mock_db.query.side_effect = Exception("connection refused")

        pair = svc_with_db.issue_token_pair(svc_with_db.admin_profile)
        with pytest.raises(DatabaseUnavailableError):
            svc_with_db.verify_access_token(pair.access_token)
        assert mock_db.rollback.called

    def test_db_exception_on_revoke_write_raises_database_unavailable(
        self,
        svc_with_db: AdminAuthService,
        mock_db: MagicMock,
    ) -> None:
        # DB query raises on revoke_token (write path)
        mock_db.query.side_effect = Exception("connection refused")

        pair = svc_with_db.issue_token_pair(svc_with_db.admin_profile)
        with pytest.raises(DatabaseUnavailableError):
            svc_with_db.revoke_token(pair.access_token)
        assert mock_db.rollback.called
