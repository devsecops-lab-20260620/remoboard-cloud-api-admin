"""Pydantic request / response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class AdminInfo(BaseModel):
    username: str
    display_name: str
    roles: list[str]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    admin: AdminInfo


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


class MeResponse(BaseModel):
    admin: AdminInfo


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------


class StatusResponse(BaseModel):
    status: str
