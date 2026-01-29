"""add total fees

Revision ID: 0f6c02463fe8
Revises: 774b47c9e4e4
Create Date: 2026-01-29 21:45:44.391144

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f6c02463fe8"
down_revision: Union[str, Sequence[str], None] = "774b47c9e4e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем колонку total_fees_usd в таблицу positions
    op.add_column(
        "positions",
        sa.Column(
            "total_fees_usd",
            sa.Float(),
            nullable=True,
            comment="Total fees value in USD (from Revert fees_value)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем колонку total_fees_usd из таблицы positions
    op.drop_column("positions", "total_fees_usd")
