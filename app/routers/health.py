"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import StatusResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=StatusResponse)
def health() -> StatusResponse:
    """Liveness probe."""
    return StatusResponse(status="ok")


@router.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "remoboard-cloud-api-admin", "status": "running"}
