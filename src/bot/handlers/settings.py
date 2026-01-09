from aiogram import Router
from aiogram.types import Message

from src.bot.keyboards.settings import get_settings_keyboard
from src.database.models import User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Создаём роутер для этого модуля
router = Router(name="settings")


@router.message(lambda message: message.text == "⚙️ Settings")
async def settings_handler(
    message: Message,
    user: User,
):
    await message.answer(
        """⚙️ Settings

Manage bot preferences.

🔔 System notifications""",
        reply_markup=get_settings_keyboard(user),
    )


@router.message(
    lambda message: message.text
    in {
        "🔕 Disable system notifications",
        "🔔 Enable system notifications",
    }
)
async def toggle_system_notifications_handler(
    message: Message,
    user: User,
    session,
):
    user.is_system_notifications_enabled = not user.is_system_notifications_enabled

    await session.commit()

    status_text = (
        "🔔 System notifications enabled"
        if user.is_system_notifications_enabled
        else "🔕 System notifications disabled"
    )

    await message.answer(
        status_text,
        reply_markup=get_settings_keyboard(user),
    )
