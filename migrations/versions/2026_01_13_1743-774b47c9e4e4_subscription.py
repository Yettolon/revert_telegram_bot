"""subscription

Revision ID: 774b47c9e4e4
Revises: 382fd05d5ceb
Create Date: 2026-01-13 17:43:46.390025

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "774b47c9e4e4"
down_revision: Union[str, Sequence[str], None] = "382fd05d5ceb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscription_tier_enum type
    subscription_tier_enum = sa.Enum(
        "FREE", "BASIC", "PRO", name="subscription_tier_enum"
    )
    subscription_tier_enum.create(op.get_bind())

    # Add subscription_tier column
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier",
            sa.Enum("FREE", "BASIC", "PRO", name="subscription_tier_enum"),
            nullable=False,
            server_default="FREE",
            comment="Current subscription tier (FREE, BASIC, PRO)",
        ),
    )

    # Add subscription_expires_at column
    op.add_column(
        "users",
        sa.Column(
            "subscription_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Subscription expiration date (None for FREE tier)",
        ),
    )

    # Create index on subscription_tier
    op.create_index("ix_users_subscription_tier", "users", ["subscription_tier"])


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_users_subscription_tier", table_name="users")

    # Drop columns
    op.drop_column("users", "subscription_expires_at")
    op.drop_column("users", "subscription_tier")

    # Drop enum type
    sa.Enum(name="subscription_tier_enum").drop(op.get_bind())
