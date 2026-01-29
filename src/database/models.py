from datetime import datetime, timezone
from functools import cached_property
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.enums import ExchangeEnum, NetworkEnum, SubscriptionTierEnum
from src.database.session import Base

user_positions = Table(
    "user_positions",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "position_id",
        Integer,
        ForeignKey("positions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "is_active",
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether the position is active for user notifications",
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Date when position was added to user",
    ),
    Index("ix_user_positions_user_active", "user_id", "is_active"),
)


class User(Base):
    """
    Telegram bot user model.

    Attributes:
        id: Internal user ID (primary key)
        telegram_id: User ID in Telegram (unique)
        username: User's Telegram username (can be None)
        first_name: User's first name
        last_name: User's last name
        created_at: User registration date and time
        updated_at: Last update date and time
        subscription_tier: Current subscription tier
        subscription_expires_at: Subscription expiration date
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="Internal user ID"
    )

    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether user is blocked",
    )

    # Telegram data
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="User ID in Telegram",
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Telegram username"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Registration date and time",
    )

    # Subscription fields
    subscription_tier: Mapped[SubscriptionTierEnum] = mapped_column(
        Enum(SubscriptionTierEnum, name="subscription_tier_enum"),
        nullable=False,
        default=SubscriptionTierEnum.FREE,
        server_default="FREE",
        index=True,
        comment="Current subscription tier (FREE, BASIC, PRO)",
    )

    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Subscription expiration date (None for FREE tier)",
    )

    # Relationships
    positions: Mapped[list["Position"]] = relationship(
        "Position",
        secondary=user_positions,
        back_populates="users",
    )

    # Notification settings
    is_system_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether system notifications are enabled for the user",
    )

    @property
    def max_positions(self) -> int:
        """Maximum number of positions allowed for user's subscription tier"""
        limits = {
            SubscriptionTierEnum.FREE: 1,
            SubscriptionTierEnum.BASIC: 5,
            SubscriptionTierEnum.PRO: 10,
        }
        return limits.get(self.subscription_tier, 1)

    @property
    def is_subscription_active(self) -> bool:
        """Check if paid subscription is active"""
        if self.subscription_tier == SubscriptionTierEnum.FREE:
            return True

        if self.subscription_expires_at is None:
            return False

        return self.subscription_expires_at > datetime.now(timezone.utc)

    @property
    def effective_subscription_tier(self) -> SubscriptionTierEnum:
        """Get effective subscription tier (FREE if expired)"""
        if self.is_subscription_active:
            return self.subscription_tier
        return SubscriptionTierEnum.FREE

    def __repr__(self) -> str:
        """String representation of user"""
        return (
            f"<User(id={self.id}, "
            f"telegram_id={self.telegram_id}, "
            f"username={self.username}, "
            f"tier={self.subscription_tier})>"
        )

    def __str__(self) -> str:
        return (
            f"<User(id={self.id}, "
            f"telegram_id={self.telegram_id}, "
            f"username={self.username})>"
        )


class Position(Base):
    """
    Позиции пользователя (one-to-many с User)
    """

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Внутренний ID позиции",
    )

    original_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=True,
        comment="Оригинальная ссылка",
    )
    revert_finance_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=True,
        comment="Revert Finance link",
    )

    exchange: Mapped[ExchangeEnum] = mapped_column(
        Enum(ExchangeEnum, name="exchange_enum"),
        nullable=False,
        index=True,
        comment="Биржа",
    )

    network: Mapped[NetworkEnum] = mapped_column(
        Enum(NetworkEnum, name="network_enum"),
        nullable=False,
        index=True,
        comment="Сеть",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания",
    )
    nft_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="ID NFT позиции",
    )

    token_1_symbol: Mapped[str] = mapped_column(
        String(64),
        nullable=True,
        comment="Символ первого токена",
    )
    token_1_address: Mapped[str] = mapped_column(
        String(42),
        nullable=True,
        comment="Адрес смарт-контракта первого токена",
    )
    token_2_symbol: Mapped[str] = mapped_column(
        String(64),
        nullable=True,
        comment="Символ второго токена",
    )
    token_2_address: Mapped[str] = mapped_column(
        String(42),
        nullable=True,
        comment="Адрес смарт-контракта второго токена",
    )
    owner_address: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="Адрес держателя позиции",
    )

    is_in_range: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="Находится ли позиция в диапазоне (Revert in_range)",
    )

    current_price: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Current price",
    )
    min_price: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Minimum price",
    )
    max_price: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Maximum price",
    )

    total_fees_usd: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="Total fees value in USD (from Revert fees_value)",
    )

    # relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_positions,
        back_populates="positions",
    )

    def __repr__(self) -> str:
        return (
            f"<Position(id={self.id}, "
            f"exchange={self.exchange}, "
            f"network={self.network})>"
        )

    @cached_property
    def revert_url(self) -> str:
        """Ссылка на позицию на Revert Finance"""
        from src.bot.tools import build_revert_position_url

        return build_revert_position_url(self.exchange, self.network, self.nft_id)
