from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

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
    Расширенный middleware, который также загружает пользователя из БД.

    Автоматически получает или создаёт пользователя на основе telegram_id
    и передаёт его в handler вместе с сессией.

    Example:
        async def handler(message: Message, session: AsyncSession, user: User):
            # user уже загружен из БД
            await message.answer(f"Привет, {user.full_name}!")
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Обработка события с загрузкой пользователя."""
        from src.database.session import async_session_maker

        if async_session_maker is None:
            raise RuntimeError("База данных не инициализирована.")

        async with async_session_maker() as session:
            data["session"] = session

            # Получаем telegram_id из события
            telegram_id = None
            if hasattr(event, "from_user") and event.from_user:
                telegram_id = event.from_user.id
            elif (
                hasattr(event, "message") and event.message and event.message.from_user
            ):
                # Для CallbackQuery
                telegram_id = event.message.from_user.id

            # Если есть telegram_id, загружаем или создаём пользователя
            if telegram_id:
                from src.database.models import User
                from sqlalchemy import select

                # Ищем пользователя
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                # Если пользователь не найден, создаём нового
                if user is None:
                    user_data = {
                        "telegram_id": telegram_id,
                    }

                    # Добавляем дополнительные данные если есть
                    if hasattr(event, "from_user"):
                        user_data.update(
                            {
                                "username": event.from_user.username,
                            }
                        )

                    user = User(**user_data)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)

                    logger.info(f"Создан новый пользователь: {user}")

                # Добавляем пользователя в data
                data["user"] = user

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
