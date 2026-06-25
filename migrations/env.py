"""Alembic environment configuration."""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make sure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import AppConfig  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401 — ensure models are registered on Base.metadata

config = context.config
target_metadata = Base.metadata

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    """Resolve the database URL from env vars or the AppConfig defaults."""
    explicit = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    return AppConfig().database_url


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    cfg_section = config.get_section(config.config_ini_section, {})
    cfg_section["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

