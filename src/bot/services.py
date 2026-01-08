from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.positions import get_positions_keyboard
from src.database.models import Position, User


async def show_positions(
    *,
    message: Message | None = None,
    callback: CallbackQuery | None = None,
    user: User,
    session: AsyncSession,
):
    result = await session.execute(
        select(Position).where(Position.users.any(User.id == user.id))
    )
    positions = result.scalars().all()

    text = "Your positions:" if positions else "You don't have any positions yet."
    keyboard = get_positions_keyboard(positions)

    if callback:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
    elif message:
        await message.answer(text, reply_markup=keyboard)
