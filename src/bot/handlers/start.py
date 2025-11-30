from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.database.models import User
from src.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаём роутер для этого модуля
router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message, user: User) -> None:
    """
    Упрощённый обработчик /start с UserSessionMiddleware.
    User автоматически загружается/создаётся middleware.
    """
    logger.info(f"Пользователь {user} вызвал /start")

    welcome_text = (
        f"👋 Привет, <b>{user.username}</b>!\n\n"
        f"Добро пожаловать в Revert Finance Bot! 🚀\n\n"
        f"Этот бот помогает отслеживать ваши позиции в DeFi.\n\n"
        f"<b>Доступные команды:</b>\n"
        f"🔹 /start - Главное меню\n"
        f"🔹 /positions - Мои позиции\n"
        f"🔹 /settings - Настройки\n"
    )

    await message.answer(welcome_text)
