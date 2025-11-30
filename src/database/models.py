from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.session import Base


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
