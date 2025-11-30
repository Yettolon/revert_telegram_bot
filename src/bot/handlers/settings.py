from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.bot.keyboards.inline import get_settings_keyboard
from src.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаём роутер для этого модуля
router = Router(name="settings")


@router.message(Command("settings"))
async def settings_handler(message: Message, user: User) -> None:
    """
    Упрощённый обработчик с UserSessionMiddleware.
    """
    settings_text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"👤 Пользователь: {user.username}\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"📅 Зарегистрирован: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        f"Выберите раздел настроек:"
    )

    await message.answer(settings_text, reply_markup=get_settings_keyboard())

    logger.info(f"Пользователь {user} открыл настройки")
