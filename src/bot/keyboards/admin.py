from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура админ-панели."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📁 Download Logs")],
            [KeyboardButton(text="🗑 Clear Logs")],
            [KeyboardButton(text="📢 Broadcast Message")],
            [KeyboardButton(text="Get Subscription Statistics")],
            [KeyboardButton(text="⬅️ Main Menu")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard


def get_broadcast_confirm_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения рассылки."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Send")],
            [KeyboardButton(text="❌ Cancel")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard
