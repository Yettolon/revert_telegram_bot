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
        f"Welcome to <b>Revert Finance</b>! 🚀\n\n"
        f"This bot helps you track your DeFi positions and get instant alerts when your pools move in or out of range.\n\n"
        f"<b>What you can do:</b>\n"
        f"📊 <b>My positions</b> - view your current pools and their status\n"
        f"⚙️ <b>Settings</b> - manage your notifications and profile preferences\n\n"
        f"Use the buttons below to get started!"
    )

    if message.from_user.id in settings.ADMIN_IDS:
        keyboard = get_admin_menu_keyboard()
    else:
        keyboard = get_main_menu_keyboard()

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
    )
