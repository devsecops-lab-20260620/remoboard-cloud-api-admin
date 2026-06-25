"""Uvicorn entry point for remoboard-cloud-api-admin."""
from __future__ import annotations

import uvicorn

from app.config import AppConfig


def main() -> None:
    config = AppConfig()
    print(f"Starting remoboard-cloud-api-admin on http://{config.host}:{config.port}")
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
