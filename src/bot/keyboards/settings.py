from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.database.models import User


def get_settings_keyboard(user: User) -> ReplyKeyboardMarkup:
    toggle_text = (
        "🔕 Disable system notifications"
        if user.is_system_notifications_enabled
        else "🔔 Enable system notifications"
    )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=toggle_text)],
            [KeyboardButton(text="⬅️ Main Menu")],
        ],
        resize_keyboard=True,
    )
