"""add prices

Revision ID: 0763ddeaa09a
Revises: 7c8a2a29c958
Create Date: 2026-01-08 19:46:57.106895

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0763ddeaa09a"
down_revision: Union[str, Sequence[str], None] = "7c8a2a29c958"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "positions",
        sa.Column(
            "current_price",
            sa.Float(),
            nullable=True,
            comment="Current price",
        ),
    )
    op.add_column(
        "positions",
        sa.Column(
            "min_price",
            sa.Float(),
            nullable=True,
            comment="Minimum price",
        ),
    )
    op.add_column(
        "positions",
        sa.Column(
            "max_price",
            sa.Float(),
            nullable=True,
            comment="Maximum price",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("positions", "max_price")
    op.drop_column("positions", "min_price")
    op.drop_column("positions", "current_price")
