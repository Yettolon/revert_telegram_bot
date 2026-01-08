from functools import wraps

from aiogram.types import Message

from src.config import settings


def admin_only(handler):
    """Декоратор для хендлеров только для админов."""

    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in settings.ADMIN_IDS:
            return
        return await handler(message, *args, **kwargs)

    return wrapper
