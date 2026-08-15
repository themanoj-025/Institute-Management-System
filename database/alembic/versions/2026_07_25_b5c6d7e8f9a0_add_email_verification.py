"""add email verification support (email_verified + verification tokens)

Revision ID: b5c6d7e8f9a0
Revises: 9a1b2c3d4e5f
Create Date: 2026-07-25 14:00:00.000000+00:00

Description
-----------
Adds email verification to the user authentication flow:

1. Adds ``email_verified`` column (Boolean, default=False) to the
   ``users`` table — new accounts start unverified.
2. Creates ``email_verification_tokens`` table — stores SHA-256 hashed
   verification tokens that are single-use and expire after 24 hours.

This enables the enforcement of email verification before first login.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "9a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email_verified column and create email_verification_tokens table."""
    # Add email_verified column to users
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Create email_verification_tokens table
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verification_user_id",
        "email_verification_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_email_verification_expires",
        "email_verification_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop email_verification_tokens table and email_verified column."""
    op.drop_index(
        "ix_email_verification_expires", table_name="email_verification_tokens"
    )
    op.drop_index(
        "ix_email_verification_user_id", table_name="email_verification_tokens"
    )
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "email_verified")
