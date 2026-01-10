"""user new field is_blocked

Revision ID: 382fd05d5ceb
Revises: 5518cd2b64d3
Create Date: 2026-01-10 11:40:01.744968

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "382fd05d5ceb"
down_revision: Union[str, Sequence[str], None] = "5518cd2b64d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_blocked")
