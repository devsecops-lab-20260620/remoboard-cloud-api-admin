from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application settings loaded from environment variables / .env file.

    Field names map directly to env-var names (case-insensitive).
    Backwards-compatible property aliases are provided so existing code
    that references ``config.admin_username`` etc. continues to work.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ── Server ────────────────────────────────────────────────────────────
    admin_api_host: str = "127.0.0.1"
    admin_api_port: int = 8000

    # ── Admin account ────────────────────────────────────────────────────
    admin_auth_username: str = "admin"
    admin_auth_password: str = "change-me-now"
    admin_auth_display_name: str = "Remoboard Administrator"

    # ── JWT ──────────────────────────────────────────────────────────────
    admin_auth_jwt_secret: str = "change-this-secret-in-production"
    admin_auth_access_token_ttl_seconds: int = 3600
    admin_auth_refresh_token_ttl_seconds: int = 604800
    admin_auth_issuer: str = "remoboard-cloud-api-admin"

    # ── Database ─────────────────────────────────────────────────────────
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "remoboard"
    db_user: str = "remoboard_admin"
    db_password: str = "please-change-me"
    # Optional full-URL override: set DATABASE_URL to skip individual vars
    database_url_override: str | None = Field(None, alias="DATABASE_URL")

    # ── Computed ─────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def _set_database_url(self) -> AppConfig:
        # store computed URL as a plain attribute for easy access
        if not self.database_url_override:
            url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
            object.__setattr__(self, "_database_url", url)
        else:
            object.__setattr__(self, "_database_url", self.database_url_override)
        return self

    @property
    def database_url(self) -> str:
        return self._database_url  # type: ignore[attr-defined]

    # ── Backwards-compatible property aliases ────────────────────────────
    @property
    def host(self) -> str:
        return self.admin_api_host

    @property
    def port(self) -> int:
        return self.admin_api_port

    @property
    def admin_username(self) -> str:
        return self.admin_auth_username

    @property
    def admin_password(self) -> str:
        return self.admin_auth_password

    @property
    def admin_display_name(self) -> str:
        return self.admin_auth_display_name

    @property
    def jwt_secret(self) -> str:
        return self.admin_auth_jwt_secret

    @property
    def access_token_ttl_seconds(self) -> int:
        return self.admin_auth_access_token_ttl_seconds

    @property
    def refresh_token_ttl_seconds(self) -> int:
        return self.admin_auth_refresh_token_ttl_seconds

    @property
    def issuer(self) -> str:
        return self.admin_auth_issuer

    # ── Factory ──────────────────────────────────────────────────────────
    @classmethod
    def from_env(cls) -> AppConfig:
        """Load config from environment / .env file."""
        return cls()
