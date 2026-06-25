"""Admin authentication router."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..auth import AdminAuthService, InvalidCredentialsError, InvalidTokenError, TokenRevokedError
from ..dependencies import get_auth_service, get_current_admin
from ..schemas import (
    LoginRequest,
    LoginResponse,
    AdminInfo,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    StatusResponse,
)

router = APIRouter(tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    auth_service: AdminAuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate and issue a token pair."""
    try:
        profile = auth_service.authenticate(request.username, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    pair = auth_service.issue_token_pair(profile)
    return LoginResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.access_expires_in,
        refresh_expires_in=pair.refresh_expires_in,
        admin=AdminInfo(**profile.to_dict()),
    )


@router.get("/me", response_model=MeResponse)
def me(claims: Dict[str, Any] = Depends(get_current_admin)) -> MeResponse:
    """Return information about the currently authenticated admin."""
    return MeResponse(
        admin=AdminInfo(
            username=claims["sub"],
            display_name=claims.get("display_name", ""),
            roles=claims.get("roles", ["admin"]),
        )
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: RefreshRequest,
    auth_service: AdminAuthService = Depends(get_auth_service),
) -> RefreshResponse:
    """Rotate tokens using a valid refresh token."""
    try:
        pair = auth_service.refresh_tokens(request.refresh_token)
    except (InvalidTokenError, TokenRevokedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return RefreshResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.access_expires_in,
        refresh_expires_in=pair.refresh_expires_in,
    )


@router.post("/logout", response_model=StatusResponse)
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    auth_service: AdminAuthService = Depends(get_auth_service),
) -> StatusResponse:
    """Revoke the current session (both access and refresh tokens are invalidated)."""
    if credentials:
        auth_service.revoke_token(credentials.credentials)
    return StatusResponse(status="logged_out")

