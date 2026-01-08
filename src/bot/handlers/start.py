from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.bot.keyboards.main import get_admin_menu_keyboard, get_main_menu_keyboard
from src.config import settings
from src.database.models import User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Создаём роутер для этого модуля
router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message, user: User) -> None:
    logger.info(f"Пользователь {user} вызвал /start")

    welcome_text = (
        f"👋 Hi, <b>{user.username}</b>!\n\n"
        f"Welcome to the Revert Finance Bot! 🚀\n\n"
        f"This bot helps you track your positions in DeFi.\n\n"
        f"<b>Available commands:</b>\n"
        f"🔹 /start - Main Menu\n"
    )

    if message.from_user.id in settings.ADMIN_IDS:
        keyboard = get_admin_menu_keyboard()
    else:
        keyboard = get_main_menu_keyboard()

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
    )
