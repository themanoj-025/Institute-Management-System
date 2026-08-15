"""Add system_config, otp_codes, revoked_tokens tables and soft-delete columns

Revision ID: 78a9b3c4d5e6
Revises: 402b6ee9301a
Create Date: 2026-07-24 08:30:00.000000+00:00

Description
-----------
Adds the following database schema changes:

New tables:
  - ``system_config`` — key/value configuration store for admin-configurable risk thresholds
  - ``otp_codes`` — server-side OTP store with hashed codes, TTL, and attempt tracking
  - ``revoked_tokens`` — JWT token blacklist storing JTIs of revoked tokens

New columns:
  - ``fees.is_deleted`` (bool, default False) + ``fees.deleted_at`` (datetime, nullable) + ``fees.deleted_by`` (FK to users)
  - ``fee_payments.is_deleted`` (bool, default False) + ``fee_payments.deleted_at`` (datetime, nullable)
  - ``results.is_deleted`` (bool, default False) + ``results.deleted_at`` (datetime, nullable)

New indexes:
  - ``ix_fees_is_deleted`` on fees.is_deleted
  - ``ix_results_is_deleted`` on results.is_deleted
  - ``ix_otp_codes_user_id_expires`` on otp_codes (user_id, expires_at)
  - ``ix_revoked_tokens_expires`` on revoked_tokens.expires_at
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78a9b3c4d5e6"
down_revision: Union[str, None] = "402b6ee9301a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New tables ─────────────────────────────────────────────────

    # system_config: key/value configuration store
    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=20), server_default="string"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_system_config_key"),
    )
    op.create_index("ix_system_config_key", "system_config", ["key"])

    # otp_codes: server-side OTP store
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0"),
        sa.Column("max_attempts", sa.Integer(), server_default="5"),
        sa.Column("is_used", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_codes_user_id", "otp_codes", ["user_id"])
    op.create_index(
        "ix_otp_codes_user_id_expires",
        "otp_codes",
        ["user_id", "expires_at"],
    )

    # revoked_tokens: JWT token blacklist
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_type", sa.String(length=20), server_default="access"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_revoked_tokens_jti"),
    )
    op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"])
    op.create_index("ix_revoked_tokens_expires", "revoked_tokens", ["expires_at"])

    # ── New columns on existing tables ──────────────────────────────

    # fees: soft-delete columns
    with op.batch_alter_table("fees") as batch_op:
        batch_op.add_column(
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True)
        )
        batch_op.create_index("ix_fees_is_deleted", ["is_deleted"])

    # fee_payments: soft-delete columns
    with op.batch_alter_table("fee_payments") as batch_op:
        batch_op.add_column(
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # results: soft-delete columns
    with op.batch_alter_table("results") as batch_op:
        batch_op.add_column(
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"))
        )
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_results_is_deleted", ["is_deleted"])


def downgrade() -> None:
    # ── Remove new columns (reverse order) ─────────────────────────

    with op.batch_alter_table("results") as batch_op:
        batch_op.drop_index("ix_results_is_deleted")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_deleted")

    with op.batch_alter_table("fee_payments") as batch_op:
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_deleted")

    with op.batch_alter_table("fees") as batch_op:
        batch_op.drop_index("ix_fees_is_deleted")
        batch_op.drop_column("deleted_by")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_deleted")

    # ── Drop new tables ────────────────────────────────────────────

    op.drop_index("ix_revoked_tokens_expires", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_jti", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")

    op.drop_index("ix_otp_codes_user_id_expires", table_name="otp_codes")
    op.drop_index("ix_otp_codes_user_id", table_name="otp_codes")
    op.drop_table("otp_codes")

    op.drop_index("ix_system_config_key", table_name="system_config")
    op.drop_table("system_config")
