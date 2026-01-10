from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для предоставления сессии базы данных в handlers.

    Автоматически создаёт сессию перед обработкой update,
    передаёт её в handler и корректно закрывает после обработки.

    Example:
        # В handler
        async def start_handler(message: Message, session: AsyncSession):
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(message.from_user.id)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Обработка события с созданием сессии БД.

        Args:
            handler: Следующий обработчик в цепочке
            event: Событие Telegram (Message, CallbackQuery и т.д.)
            data: Данные, передаваемые между middleware и handlers

        Returns:
            Результат обработки handler
        """
        # Импортируем async_session_maker здесь, а не в начале файла
        # Это гарантирует, что мы получим актуальное значение
        from src.database.session import async_session_maker

        # Проверяем, что async_session_maker инициализирован
        if async_session_maker is None:
            logger.error("Database session maker не инициализирован!")
            raise RuntimeError(
                "База данных не инициализирована. "
                "Убедитесь, что init_db() вызвана при запуске."
            )

        # Создаём новую сессию для этого запроса
        async with async_session_maker() as session:
            # Добавляем сессию в data для доступа в handlers
            data["session"] = session

            try:
                # Вызываем следующий обработчик
                result = await handler(event, data)

                # Автоматический commit после успешной обработки
                await session.commit()

                return result

            except Exception as e:
                # В случае ошибки откатываем транзакцию
                await session.rollback()
                logger.error(f"Ошибка при обработке события: {e}", exc_info=True)
                raise


class DatabaseSessionMiddleware(BaseMiddleware):
    """
    Альтернативная версия middleware с явным контролем commit/rollback.

    В этой версии handler должен сам вызывать session.commit()
    для сохранения изменений. Это даёт больше контроля, но требует
    дисциплины от разработчиков.

    Example:
        async def handler(message: Message, session: AsyncSession):
            user = User(telegram_id=message.from_user.id)
            session.add(user)
            await session.commit()  # Явный commit
    """

    def __init__(self, auto_commit: bool = False):
        """
        Инициализация middleware.

        Args:
            auto_commit: Автоматически делать commit после handler.
                        По умолчанию False - handler должен сам коммитить.
        """
        super().__init__()
        self.auto_commit = auto_commit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события."""
        from src.database.session import async_session_maker

        if async_session_maker is None:
            logger.error("Database session maker не инициализирован!")
            raise RuntimeError("База данных не инициализирована.")

        async with async_session_maker() as session:
            data["session"] = session

            try:
                result = await handler(event, data)

                # Опциональный auto-commit
                if self.auto_commit:
                    await session.commit()

                return result

            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при обработке: {e}", exc_info=True)
                raise


class UserSessionMiddleware(BaseMiddleware):
    """
    Middleware, который загружает пользователя из БД или создаёт нового.
    Гарантированно безопасно при параллельных запросах.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from src.database.models import User
        from src.database.session import async_session_maker

        if async_session_maker is None:
            raise RuntimeError("База данных не инициализирована.")

        async with async_session_maker() as session:
            data["session"] = session

            # Aiogram автоматически добавляет event_from_user в data
            telegram_user = data.get("event_from_user")

            user = None
            if telegram_user:
                telegram_id = telegram_user.id
                username = telegram_user.username

                # Пытаемся вставить пользователя безопасно
                stmt = (
                    insert(User)
                    .values(
                        telegram_id=telegram_id,
                        username=username,
                    )
                    .on_conflict_do_nothing(index_elements=["telegram_id"])
                )
                await session.execute(stmt)

                # Загружаем пользователя из базы
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one()

                if user.is_blocked:
                    return

                data["user"] = user
            else:
                logger.warning("event_from_user отсутствует в контексте")

            try:
                result = await handler(event, data)
                await session.commit()
                return result

            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при обработке: {e}", exc_info=True)
                raise


# Алиасы для удобства
DBMiddleware = DatabaseMiddleware
DBSessionMiddleware = DatabaseSessionMiddleware
