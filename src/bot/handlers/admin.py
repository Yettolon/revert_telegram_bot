from pathlib import Path

from aiogram import Router
from aiogram.types import FSInputFile, Message

from src.bot.keyboards.admin import get_admin_panel_keyboard
from src.bot.keyboards.main import get_admin_menu_keyboard
from src.bot.permissions import admin_only
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

LOGS_DIR = Path("logs")

# Создаём роутер для этого модуля
router = Router(name="admin")


@router.message(lambda message: message.text == "🛠 Admin Panel")
@admin_only
async def admin_panel_handler(message: Message):
    """Открываем админскую панель."""
    await message.answer(
        "🛠 Welcome to the Admin Panel!\nPlease select an action:",
        reply_markup=get_admin_panel_keyboard(),
    )


@router.message(lambda message: message.text == "⬅️ Main Menu")
async def back_to_main_menu_handler(message: Message):
    """Возврат в главное меню."""
    welcome_text = "👋 Welcome to the Main Menu!\nChoose a section:"

    keyboard = get_admin_menu_keyboard()

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
    )


@router.message(lambda message: message.text == "📁 Download Logs")
@admin_only
async def send_logs_handler(message: Message):
    """Send all log files from the logs folder to the admin."""
    if not LOGS_DIR.exists() or not any(LOGS_DIR.iterdir()):
        await message.answer("📁 No logs found.")
        return

    await message.answer("📤 Starting log export...")

    for log_file in LOGS_DIR.iterdir():
        if log_file.is_file():
            await message.answer_document(
                FSInputFile(log_file), caption=f"Log file: {log_file.name}"
            )

    await message.answer(
        "✅ All logs have been sent.", reply_markup=get_admin_menu_keyboard()
    )
