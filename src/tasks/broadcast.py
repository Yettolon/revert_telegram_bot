import asyncio

import uvloop
from aiogram import Bot
from aiogram.types import MessageEntity
from sqlalchemy import select, update

from src.celery import celery_app
from src.config import settings
from src.database.models import User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@celery_app.task(name="src.tasks.broadcast.send_broadcast")
def send_broadcast_task(message_data: dict) -> dict:
    """
    Celery таска для рассылки сообщений всем пользователям.

    Рассылка идет только юзерам с:
    - is_system_notifications_enabled = True
    - is_blocked = False

    Args:
        message_data: Данные сообщения (type, text, file_id, entities)

    Returns:
        dict: Статистика рассылки (total, success, failed, blocked)
    """
    try:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_send_broadcast(message_data))
        finally:
            loop.run_until_complete(_cleanup_db())
            loop.close()
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
        logger.info("База данных инициализирована в Celery worker")

    bot = Bot(token=settings.BOT_TOKEN)

    try:
        # Получаем пользователей с включенными уведомлениями и не заблокированных
        async with db_session.async_session_maker() as session:
            result = await session.execute(
                select(User).where(
                    User.is_system_notifications_enabled == True,
                    User.is_blocked == False,
                )
            )
            users = result.scalars().all()

        total = len(users)
        success = 0
        failed = 0
        blocked = 0

        logger.info(f"Starting broadcast to {total} users (with notifications enabled)")

        # Восстанавливаем entities если есть
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
                # Отправляем сообщение в зависимости от типа
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
                else:  # text
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_data["text"],
                        entities=entities,
                    )

                success += 1
                logger.debug(f"Message sent to user {user.telegram_id}")

                # Небольшая задержка, чтобы не словить флуд (20 msg/sec limit)
                await asyncio.sleep(0.05)

            except Exception as e:
                error_str = str(e).lower()

                # Проверяем, заблокировал ли пользователь бота
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

                    # Помечаем юзера как заблокированного
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

    except Exception as e:
        logger.error(f"Broadcast task failed: {e}")
        raise
    finally:
        await bot.session.close()


@celery_app.task(name="src.tasks.broadcast.get_broadcast_stats")
def get_broadcast_stats_task(task_id: str) -> dict:
    """Получить статистику по конкретной рассылке."""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "state": result.state,
        "result": result.result if result.ready() else None,
    }
