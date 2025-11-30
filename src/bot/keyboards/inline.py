from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура главного меню настроек.

    Returns:
        InlineKeyboardMarkup: Клавиатура настроек
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔔 Уведомления", callback_data="settings_notifications"
        )
    )
    builder.row(
        InlineKeyboardButton(text="👛 Мои кошельки", callback_data="settings_wallets")
    )
    builder.row(InlineKeyboardButton(text="ℹ️ О боте", callback_data="settings_about"))

    return builder.as_markup()
