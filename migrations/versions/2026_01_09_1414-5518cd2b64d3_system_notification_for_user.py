"""system notification for user

Revision ID: 5518cd2b64d3
Revises: 0763ddeaa09a
Create Date: 2026-01-09 14:14:26.995071

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5518cd2b64d3"
down_revision: Union[str, Sequence[str], None] = "0763ddeaa09a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_system_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether system notifications are enabled for the user",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_system_notifications_enabled")
