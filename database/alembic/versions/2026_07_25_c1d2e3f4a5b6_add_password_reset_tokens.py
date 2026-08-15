"""add password_reset_tokens table

Revision ID: c1d2e3f4a5b6
Revises: b5c6d7e8f9a0
Create Date: 2026-07-25 14:00:00.000000+00:00

Description
-----------
Creates the ``password_reset_tokens`` table for the self-service
password-reset flow. Tokens are SHA-256 hashed before storage,
single-use, and expire after 30 minutes.

The table supports:
  - ``user_id`` (FK to users) — the user requesting the reset
  - ``token_hash`` (SHA-256 hex digest) — never store raw token
  - ``expires_at`` (TIMESTAMPTZ) — 30-minute TTL
  - ``used_at`` (TIMESTAMPTZ, nullable) — set on consumption
  - ``created_at`` (TIMESTAMPTZ) — token creation timestamp

Indexes on ``user_id`` and ``expires_at`` for efficient lookups.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the password_reset_tokens table."""
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_expires",
        "password_reset_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop the password_reset_tokens table and its indexes."""
    op.drop_index("ix_password_reset_expires", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
