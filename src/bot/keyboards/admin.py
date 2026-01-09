from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура админ-панели."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📁 Download Logs")],
            [KeyboardButton(text="🗑 Clear Logs")],
            [KeyboardButton(text="⬅️ Main Menu")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard
