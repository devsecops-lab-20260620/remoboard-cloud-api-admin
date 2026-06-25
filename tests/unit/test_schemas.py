"""Unit tests — Pydantic schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import LoginRequest, RefreshRequest


class TestLoginRequest:
    def test_valid(self) -> None:
        req = LoginRequest(username="admin", password="pass")
        assert req.username == "admin"
        assert req.password == "pass"

    def test_empty_username_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="pass")

    def test_empty_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="")

    def test_missing_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(username="admin")  # type: ignore[call-arg]


class TestRefreshRequest:
    def test_valid(self) -> None:
        req = RefreshRequest(refresh_token="some.jwt.token")
        assert req.refresh_token == "some.jwt.token"

    def test_empty_token_raises(self) -> None:
        with pytest.raises(ValidationError):
            RefreshRequest(refresh_token="")

