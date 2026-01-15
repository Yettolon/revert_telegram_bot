from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню бота: клавиатура снизу.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 My positions"),
                KeyboardButton(text="⚙️ Settings"),
            ],
            [
                KeyboardButton(text="💎 Subscription"),
            ],
        ],
        resize_keyboard=True,  # уменьшает кнопки под размер экрана
        one_time_keyboard=False,  # клавиатура остаётся видимой
    )
    return keyboard


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 My positions"),
                KeyboardButton(text="⚙️ Settings"),
            ],
            [
                KeyboardButton(text="💎 Subscription"),
            ],
            [KeyboardButton(text="🛠 Admin Panel")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard
