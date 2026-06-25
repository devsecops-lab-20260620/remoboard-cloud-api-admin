"""Initial schema — admin revocation tables.

Revision ID: 0001
Revises: (initial)
Create Date: 2026-06-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None
# ---------------------------------------------------------------------------


def upgrade() -> None:
    op.create_table(
        "admin_revoked_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(
        op.f("ix_admin_revoked_tokens_jti"),
        "admin_revoked_tokens",
        ["jti"],
        unique=True,
    )

    op.create_table(
        "admin_revoked_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sid", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sid"),
    )
    op.create_index(
        op.f("ix_admin_revoked_sessions_sid"),
        "admin_revoked_sessions",
        ["sid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_revoked_sessions_sid"), table_name="admin_revoked_sessions")
    op.drop_table("admin_revoked_sessions")

    op.drop_index(op.f("ix_admin_revoked_tokens_jti"), table_name="admin_revoked_tokens")
    op.drop_table("admin_revoked_tokens")
