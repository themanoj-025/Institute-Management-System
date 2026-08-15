"""convert datetime columns to timezone-aware (TIMESTAMPTZ)

Revision ID: 9a1b2c3d4e5f
Revises: 78a9b3c4d5e6
Create Date: 2026-07-25 10:00:00.000000+00:00

Description
-----------
Converts all TIMESTAMP WITHOUT TIME ZONE columns to TIMESTAMP WITH TIME ZONE
(TIMESTAMPTZ) to match the model layer's ``DateTime(timezone=True)`` declarations.

Why this is needed
------------------
The SQLAlchemy models now declare ``DateTime(timezone=True)`` on all timestamp
columns and ``utc_now()`` returns timezone-aware datetimes. The existing
PostgreSQL columns are ``TIMESTAMP WITHOUT TIME ZONE`` and will reject
timezone-aware Python datetime values at runtime.

Migration approach
------------------
Each ``ALTER COLUMN`` uses ``<column> AT TIME ZONE 'UTC'`` to reinterpret
existing naive values (which are already UTC) as timezone-aware without
shifting the actual time value.

SQLite note
-----------
SQLite has no native ``TIMESTAMPTZ`` type — SQLAlchemy handles
``DateTime(timezone=True)`` at the Python/dialect level for SQLite. No
equivalent SQLite migration is needed; this migration is PostgreSQL-only.
If run against SQLite, these ALTER statements will be no-ops (SQLite ignores
type modifier changes).

Downgrade note
--------------
The downgrade converts back to ``TIMESTAMP WITHOUT TIME ZONE`` using
``AT TIME ZONE 'UTC'`` in reverse. This strips the ``tzinfo``, which is a
documented, expected lossy operation: round-tripping a timezone-aware value
through a naive column is inherently lossy.
"""

from typing import List, Sequence, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, None] = "78a9b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enumeration of every table/column pair that needs conversion
# Cross-referenced against all model classes that declare
# ``DateTime(timezone=True)``.
#
# Format: (table, column)

TIMESTAMPZ_COLUMNS: List[Tuple[str, str]] = [
    ("users", "locked_until"),
    ("users", "created_at"),
    ("users", "updated_at"),
    ("courses", "created_at"),
    ("results", "deleted_at"),
    ("leaves", "applied_on"),
    ("leaves", "reviewed_on"),
    ("feedbacks", "submitted_on"),
    ("feedbacks", "replied_on"),
    ("fees", "deleted_at"),
    ("fee_payments", "payment_date"),
    ("fee_payments", "deleted_at"),
    ("notices", "created_at"),
    ("activity_logs", "timestamp"),
    ("enquiries", "submitted_at"),
    ("enquiries", "resolved_at"),
    ("system_config", "updated_at"),
    ("otp_codes", "expires_at"),
    ("otp_codes", "created_at"),
    ("revoked_tokens", "revoked_at"),
    ("revoked_tokens", "expires_at"),
]


def upgrade() -> None:
    """Convert all timestamp columns to TIMESTAMPTZ and create promotion_history table.

    1. For each existing column, ALTER the type using
       ``USING <col> AT TIME ZONE 'UTC'`` to reinterpret existing naive UTC values
       as timezone-aware with ``+00:00`` offset.
    2. Create the ``promotion_history`` table for ML model promotion tracking.
    """
    for table, column in TIMESTAMPZ_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMPTZ "
            f"USING {column} AT TIME ZONE 'UTC'"
        )

    # ── Create promotion_history table ─────────────────────────────────
    op.create_table(
        "promotion_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("candidate_model_version", sa.String(length=100), nullable=False),
        sa.Column("candidate_auroc", sa.Float(), nullable=True),
        sa.Column("candidate_f1", sa.Float(), nullable=True),
        sa.Column("candidate_precision", sa.Float(), nullable=True),
        sa.Column("candidate_recall", sa.Float(), nullable=True),
        sa.Column("active_model_version", sa.String(length=100), nullable=True),
        sa.Column("active_auroc", sa.Float(), nullable=True),
        sa.Column("promoted", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_promotion_history_timestamp",
        "promotion_history",
        ["timestamp"],
    )
    op.create_index(
        "ix_promotion_history_promoted",
        "promotion_history",
        ["promoted"],
    )


def downgrade() -> None:
    """Revert all timestamp columns back to TIMESTAMP WITHOUT TIME ZONE
    and drop the promotion_history table.

    .. warning::
        Downgrade is lossy. Timezone-aware values round-tripped through
        ``TIMESTAMP WITHOUT TIME ZONE`` lose their ``tzinfo`` permanently.
    """
    # Drop promotion_history table first
    op.drop_index("ix_promotion_history_promoted", table_name="promotion_history")
    op.drop_index("ix_promotion_history_timestamp", table_name="promotion_history")
    op.drop_table("promotion_history")

    # Revert timestamp columns
    for table, column in TIMESTAMPZ_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )
