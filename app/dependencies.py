"""FastAPI dependency providers."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .auth import AdminAuthService, InvalidTokenError, TokenRevokedError
from .config import AppConfig
from .database import get_db

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()


# ---------------------------------------------------------------------------
# Auth service
# ---------------------------------------------------------------------------


def get_auth_service(
    config: AppConfig = Depends(get_config),
    db: Optional[Session] = Depends(get_db),
) -> AdminAuthService:
    return AdminAuthService(config=config, db=db)


# ---------------------------------------------------------------------------
# Bearer token extractor
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    auth_service: AdminAuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Validate the Bearer token and return JWT claims."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        return auth_service.verify_access_token(credentials.credentials)
    except (InvalidTokenError, TokenRevokedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

