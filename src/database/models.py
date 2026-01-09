from datetime import datetime
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

from src.database.enums import ExchangeEnum, NetworkEnum
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
        comment="Активна ли позиция для уведомлений пользователя",
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата добавления позиции пользователю",
    ),
    Index("ix_user_positions_user_active", "user_id", "is_active"),
)


class User(Base):
    """
    Модель пользователя телеграм-бота.

    Attributes:
        id: Внутренний ID пользователя (primary key)
        telegram_id: ID пользователя в Telegram (уникальный)
        username: Username пользователя в Telegram (может быть None)
        first_name: Имя пользователя
        last_name: Фамилия пользователя
        created_at: Дата и время регистрации пользователя
        updated_at: Дата и время последнего обновления
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="Внутренний ID пользователя"
    )

    # Telegram данные
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="ID пользователя в Telegram",
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Username в Telegram"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата и время регистрации",
    )
    positions: Mapped[list["Position"]] = relationship(
        "Position",
        secondary=user_positions,
        back_populates="users",
    )

    # notification
    is_system_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether system notifications are enabled for the user",
    )

    @cached_property
    def positions_count(self) -> int:
        """Общее количество позиций пользователя (кешируется)"""
        return len(self.positions)

    @cached_property
    def active_positions_count(self) -> int:
        """Количество активных позиций (кешируется)"""
        # Для этого нужно получить данные из ассоциативной таблицы
        # Здесь используем простой подсчет, но можно оптимизировать
        if not hasattr(self, "_positions_loaded"):
            return 0
        return sum(1 for pos in self.positions if self._is_position_active(pos))

    @cached_property
    def in_range_positions_count(self) -> int:
        """Количество позиций в диапазоне (кешируется)"""
        return sum(1 for pos in self.positions if pos.is_in_range)

    @cached_property
    def out_of_range_positions_count(self) -> int:
        """Количество позиций вне диапазона (кешируется)"""
        return sum(1 for pos in self.positions if not pos.is_in_range)

    def clear_cache(self):
        """Очистка кешированных свойств"""
        for attr in [
            "positions_count",
            "active_positions_count",
            "in_range_positions_count",
            "out_of_range_positions_count",
        ]:
            if attr in self.__dict__:
                del self.__dict__[attr]

    def __repr__(self) -> str:
        """Строковое представление пользователя."""
        return (
            f"<User(id={self.id}, "
            f"telegram_id={self.telegram_id}, "
            f"username={self.username})>"
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
