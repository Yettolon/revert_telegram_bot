"""revert_url

Revision ID: 7c8a2a29c958
Revises: a2e22ba01b30
Create Date: 2026-01-01 13:25:46.523837

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c8a2a29c958"
down_revision: Union[str, Sequence[str], None] = "a2e22ba01b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "positions",
        sa.Column(
            "revert_finance_url",
            sa.String(length=1024),
            nullable=True,
            comment="Revert Finance link",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("positions", "revert_finance_url")
