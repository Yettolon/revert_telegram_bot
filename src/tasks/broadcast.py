import asyncio

from aiogram import Bot
from aiogram.types import MessageEntity
from sqlalchemy import select, update

from src.config import settings
from src.database.models import User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def send_broadcast_task(message_data: dict) -> dict:
    """
    Асинхронная функция рассылки.
    Вызывается из aiogram через await или asyncio.create_task().
    """
    try:
        result = await _send_broadcast(message_data)
        await _cleanup_db()
        return result
    except Exception:
        logger.exception("Ошибка при выполнении broadcast таски")
        raise


async def _cleanup_db():
    """Закрывает все соединения с БД."""
    from src.database import session as db_session

    if db_session.engine is not None:
        await db_session.engine.dispose()
        logger.info("Database connections closed")


async def _send_broadcast(message_data: dict) -> dict:
    """Асинхронная функция рассылки."""
    from src.database import session as db_session

    # Инициализируем БД если нужно
    if db_session.async_session_maker is None:
        await db_session.init_db()
        logger.info("База данных инициализирована")

    bot = Bot(token=settings.BOT_TOKEN)

    try:
        # Получаем пользователей
        async with db_session.async_session_maker() as session:
            result = await session.execute(
                select(User).where(
                    User.is_system_notifications_enabled.is_(True),
                    User.is_blocked.is_(False),
                )
            )
            users = result.scalars().all()

        total = len(users)
        success = 0
        failed = 0
        blocked = 0

        logger.info(f"Starting broadcast to {total} users")

        # Восстанавливаем entities
        entities = None
        if message_data.get("entities"):
            entities = [
                MessageEntity(
                    type=e["type"],
                    offset=e["offset"],
                    length=e["length"],
                    url=e.get("url"),
                )
                for e in message_data["entities"]
            ]

        for user in users:
            try:
                if message_data["type"] == "photo":
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=message_data["file_id"],
                        caption=message_data.get("text"),
                        caption_entities=entities,
                    )
                elif message_data["type"] == "video":
                    await bot.send_video(
                        chat_id=user.telegram_id,
                        video=message_data["file_id"],
                        caption=message_data.get("text"),
                        caption_entities=entities,
                    )
                elif message_data["type"] == "document":
                    await bot.send_document(
                        chat_id=user.telegram_id,
                        document=message_data["file_id"],
                        caption=message_data.get("text"),
                        caption_entities=entities,
                    )
                else:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_data["text"],
                        entities=entities,
                    )

                success += 1
                await asyncio.sleep(0.05)

            except Exception as e:
                error_str = str(e).lower()

                if any(
                    phrase in error_str
                    for phrase in [
                        "bot was blocked",
                        "user is deactivated",
                        "bot can't initiate",
                        "forbidden",
                    ]
                ):
                    blocked += 1
                    logger.warning(f"User {user.telegram_id} blocked the bot: {e}")

                    async with db_session.async_session_maker() as session:
                        await session.execute(
                            update(User)
                            .where(User.telegram_id == user.telegram_id)
                            .values(is_blocked=True)
                        )
                        await session.commit()
                else:
                    failed += 1
                    logger.error(f"Failed to send to {user.telegram_id}: {e}")

        result = {
            "total": total,
            "success": success,
            "failed": failed,
            "blocked": blocked,
        }

        logger.info(
            f"Broadcast completed: {success}/{total} sent successfully, "
            f"{blocked} blocked, {failed} failed"
        )
        return result

    finally:
        await bot.session.close()
