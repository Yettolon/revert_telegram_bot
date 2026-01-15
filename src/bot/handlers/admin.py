from pathlib import Path

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from src.bot.keyboards.admin import (
    get_admin_panel_keyboard,
    get_broadcast_confirm_keyboard,
    get_cancel_keyboard,
)
from src.bot.keyboards.main import get_admin_menu_keyboard, get_main_menu_keyboard
from src.bot.permissions import admin_only
from src.bot.states.admin import BroadcastStates
from src.config import settings
from src.services.subscription import get_subscription_stats
from src.tasks.broadcast import send_broadcast_task
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
    welcome_text = (
        "🏠 You are back at the Main Menu.\n\n"
        "Use the buttons below to view your positions or adjust your settings."
    )

    if message.from_user.id in settings.ADMIN_IDS:
        keyboard = get_admin_menu_keyboard()
    else:
        keyboard = get_main_menu_keyboard()

    await message.answer(
        welcome_text,
        reply_markup=keyboard,
    )


@router.message(lambda message: message.text == "📁 Download Logs")
@admin_only
async def send_logs_handler(message: Message):
    """Send all non-empty log files from the logs folder to the admin."""
    if not LOGS_DIR.exists():
        await message.answer("📁 Logs folder does not exist.")
        return

    log_files = [f for f in LOGS_DIR.iterdir() if f.is_file() and f.stat().st_size > 0]

    if not log_files:
        await message.answer("📁 No non-empty logs found.")
        return

    await message.answer("📤 Starting log export...")

    for log_file in log_files:
        await message.answer_document(
            FSInputFile(log_file),
            caption=f"Log file: {log_file.name}",
        )

    empty = len(
        [f for f in LOGS_DIR.iterdir() if f.is_file() and f.stat().st_size == 0]
    )

    await message.answer(
        f"📤 Logs sent.\n" f"📄 Sent: {len(log_files)}\n" f"⚠️ Empty skipped: {empty}",
    )


@router.message(lambda message: message.text == "🗑 Clear Logs")
@admin_only
async def clear_logs_handler(message: Message):
    """Clear log files without deleting them."""
    if not LOGS_DIR.exists() or not any(LOGS_DIR.iterdir()):
        await message.answer("📁 Logs folder is empty.")
        return

    cleared = 0

    for log_file in LOGS_DIR.iterdir():
        if log_file.is_file():
            with open(log_file, "w"):
                pass
            cleared += 1

    await message.answer(
        f"🧹 Logs cleared.\nFiles cleaned: <b>{cleared}</b>",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard(),
    )


@router.message(lambda message: message.text == "📢 Broadcast Message")
@admin_only
async def start_broadcast_handler(message: Message, state: FSMContext):
    """Начинаем процесс рассылки."""
    await state.set_state(BroadcastStates.waiting_for_message)
    await message.answer(
        "📝 Send me the message you want to broadcast.\n"
        "You can send text, photo, video, or document.\n\n"
        "Press 'Cancel' to abort.",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(
    lambda message: message.text == "❌ Cancel", BroadcastStates.waiting_for_message
)
@admin_only
async def cancel_broadcast_handler(message: Message, state: FSMContext):
    """Отмена рассылки."""
    await state.clear()
    await message.answer(
        "❌ Broadcast cancelled.",
        reply_markup=get_admin_panel_keyboard(),
    )


@router.message(BroadcastStates.waiting_for_message)
@admin_only
async def receive_broadcast_message(message: Message, state: FSMContext):
    """Получаем сообщение для рассылки и показываем превью."""
    # Сохраняем данные сообщения
    message_data = {
        "text": message.text or message.caption,
        "entities": None,
    }

    # Определяем тип контента
    if message.photo:
        message_data["type"] = "photo"
        message_data["file_id"] = message.photo[-1].file_id
        if message.caption_entities:
            message_data["entities"] = [
                {"type": e.type, "offset": e.offset, "length": e.length, "url": e.url}
                for e in message.caption_entities
            ]
    elif message.video:
        message_data["type"] = "video"
        message_data["file_id"] = message.video.file_id
        if message.caption_entities:
            message_data["entities"] = [
                {"type": e.type, "offset": e.offset, "length": e.length, "url": e.url}
                for e in message.caption_entities
            ]
    elif message.document:
        message_data["type"] = "document"
        message_data["file_id"] = message.document.file_id
        if message.caption_entities:
            message_data["entities"] = [
                {"type": e.type, "offset": e.offset, "length": e.length, "url": e.url}
                for e in message.caption_entities
            ]
    elif message.text:
        message_data["type"] = "text"
        if message.entities:
            message_data["entities"] = [
                {"type": e.type, "offset": e.offset, "length": e.length, "url": e.url}
                for e in message.entities
            ]
    else:
        await message.answer(
            "❌ Unsupported message type. Please send text, photo, video, or document.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Сохраняем в state
    await state.update_data(message_data=message_data)
    await state.set_state(BroadcastStates.waiting_for_confirmation)

    # Показываем превью
    await message.answer(
        "📋 <b>Preview of your broadcast message:</b>", parse_mode="HTML"
    )

    # Отправляем копию сообщения
    if message_data["type"] == "photo":
        await message.answer_photo(
            photo=message_data["file_id"],
            caption=message_data["text"],
        )
    elif message_data["type"] == "video":
        await message.answer_video(
            video=message_data["file_id"],
            caption=message_data["text"],
        )
    elif message_data["type"] == "document":
        await message.answer_document(
            document=message_data["file_id"],
            caption=message_data["text"],
        )
    else:
        await message.answer(message_data["text"])

    await message.answer(
        "❓ Send this message to all users?",
        reply_markup=get_broadcast_confirm_keyboard(),
    )


@router.message(
    lambda message: message.text == "✅ Send", BroadcastStates.waiting_for_confirmation
)
@admin_only
async def confirm_broadcast_handler(message: Message, state: FSMContext):
    """Подтверждаем и запускаем рассылку."""
    data = await state.get_data()
    message_data = data.get("message_data")

    if not message_data:
        await message.answer("❌ Message data not found. Please try again.")
        await state.clear()
        return

    # Запускаем Celery таску
    task = send_broadcast_task.delay(message_data)

    await state.clear()
    await message.answer(
        f"✅ Broadcast started!\n"
        f"Task ID: <code>{task.id}</code>\n\n"
        f"Messages will be sent to all users in background.",
        parse_mode="HTML",
        reply_markup=get_admin_panel_keyboard(),
    )

    logger.info(f"Broadcast task started: {task.id}")


@router.message(
    lambda message: message.text == "❌ Cancel",
    BroadcastStates.waiting_for_confirmation,
)
@admin_only
async def cancel_confirmation_handler(message: Message, state: FSMContext):
    """Отмена на этапе подтверждения."""
    await state.clear()
    await message.answer(
        "❌ Broadcast cancelled.",
        reply_markup=get_admin_panel_keyboard(),
    )


@router.message(lambda message: message.text == "Get Subscription Statistics")
@admin_only
async def get_subsctiption_stats(message: Message, session):
    stats = await get_subscription_stats(session)
    await message.answer(
        f"📊 Subscription Statistics:\n"
        f"Free: {stats['free']}\n"
        f"Basic: {stats['basic']}\n"
        f"Pro: {stats['pro']}\n"
        f"Active Paid: {stats['active_paid']}\n"
        f"Total: {stats['total']}"
    )
