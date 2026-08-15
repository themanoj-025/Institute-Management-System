"""baseline

Revision ID: 402b6ee9301a
Revises:
Create Date: 2026-07-24 08:24:13.875607+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "402b6ee9301a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
