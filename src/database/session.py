from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# Базовый класс для моделей
class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""


# Глобальные переменные для engine и session maker
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Создание и настройка движка базы данных.

    Returns:
        AsyncEngine: Асинхронный движок SQLAlchemy
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.DEBUG,  # Логирование SQL запросов в debug режиме
        pool_pre_ping=True,  # Проверка соединения перед использованием
        pool_size=10,  # Размер пула соединений
        max_overflow=20,  # Максимальное количество дополнительных соединений
        pool_recycle=3600,  # Переподключение каждый час
        # Для Docker можно использовать NullPool если нужно
        # poolclass=NullPool,
    )


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Создание фабрики сессий.

    Returns:
        async_sessionmaker: Фабрика для создания сессий
    """
    global engine
    if engine is None:
        engine = get_engine()

    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Объекты остаются доступными после commit
        autoflush=False,  # Ручной контроль flush
        autocommit=False,  # Ручной контроль commit
    )


async def init_db() -> None:
    """
    Инициализация базы данных.
    Подключение к БД и создание session maker.
    Таблицы создаются через миграции, а не автоматически.
    """
    global engine, async_session_maker

    try:
        logger.info("Инициализация базы данных...")

        # Создание engine
        engine = get_engine()

        # Создание session maker
        async_session_maker = get_session_maker()

        logger.info("База данных успешно инициализирована (без автосоздания таблиц)")

    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """
    Закрытие всех соединений с базой данных.
    """
    global engine, async_session_maker

    try:
        logger.info("Закрытие соединений с базой данных...")

        if engine is not None:
            await engine.dispose()
            engine = None

        async_session_maker = None

        logger.info("Соединения с базой данных закрыты")

    except Exception as e:
        logger.error(f"Ошибка при закрытии соединений с БД: {e}", exc_info=True)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор для получения сессии базы данных.
    Используется в middleware и для прямого доступа.

    Yields:
        AsyncSession: Сессия базы данных

    Example:
        async with get_session() as session:
            user = await session.get(User, user_id)
    """
    global async_session_maker

    if async_session_maker is None:
        raise RuntimeError(
            "База данных не инициализирована. "
            "Вызовите init_db() перед использованием."
        )

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при работе с БД: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def create_session() -> AsyncSession:
    """
    Создание новой сессии базы данных.
    Используется когда нужна сессия без контекстного менеджера.

    Returns:
        AsyncSession: Новая сессия базы данных

    Note:
        Не забудьте закрыть сессию после использования:
        session = await create_session()
        try:
            # работа с сессией
            await session.commit()
        finally:
            await session.close()
    """
    global async_session_maker

    if async_session_maker is None:
        raise RuntimeError(
            "База данных не инициализирована. "
            "Вызовите init_db() перед использованием."
        )

    return async_session_maker()


# Для удобства импорта
__all__ = [
    "Base",
    "init_db",
    "close_db",
    "get_session",
    "create_session",
    "get_engine",
    "get_session_maker",
]
