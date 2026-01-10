from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.positions import get_positions_keyboard
from src.config import settings
from src.database.models import Position, User, user_positions


async def show_positions(
    *,
    message: Message | None = None,
    callback: CallbackQuery | None = None,
    user: User,
    session: AsyncSession,
):
    result = await session.execute(
        select(
            Position,
            user_positions.c.is_active,
        )
        .join(user_positions, user_positions.c.position_id == Position.id)
        .where(user_positions.c.user_id == user.id)
        .order_by(Position.created_at.desc())
    )

    rows: list[tuple[Position, bool]] = result.all()

    text = "Your positions:" if rows else "You don't have any positions yet."

    keyboard = get_positions_keyboard(rows)

    if callback:
        try:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
            )
        except Exception:
            await callback.message.answer(
                text,
                reply_markup=keyboard,
            )
        await callback.answer()
    elif message:
        await message.answer(
            text,
            reply_markup=keyboard,
        )


async def render_position_detail(
    *,
    message: Message,
    session: AsyncSession,
    user: User,
    position_id: int,
):
    result = await session.execute(select(Position).where(Position.id == position_id))
    position = result.scalar_one_or_none()

    if not position:
        await message.answer("Position not found.")
        return

    result = await session.execute(
        select(user_positions.c.is_active).where(
            user_positions.c.user_id == user.id,
            user_positions.c.position_id == position.id,
        )
    )
    is_active = result.scalar_one()

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔗 View on Revert Finance",
            url=position.revert_url,
        )
    )

    if position.owner_address:
        builder.row(
            InlineKeyboardButton(
                text="👉 View on DeBank",
                url=f"{settings.DEBANK_PROFILE_URL}{position.owner_address}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔕 Disable notifications" if is_active else "🔔 Enable notifications",
            callback_data=f"toggle_position_notify_{position.id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="❌ Delete Position",
            callback_data=f"delete_position_{position.id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ Back to positions",
            callback_data="positions_back",
        )
    )

    status_emoji = "🟢" if position.is_in_range else "🔴"
    status_text = "In range" if position.is_in_range else "Out of range"

    await message.edit_text(
        f"{status_emoji} <b>{status_text}</b>\n"
        f"Exchange: {position.exchange.value}\n"
        f"Network: {position.network.value}\n"
        f"NFT ID: {position.nft_id}\n"
        f"Current price: {position.current_price:.6f}\n"
        f"Min price: {position.min_price:.6f}\n"
        f"Max price: {position.max_price:.6f}\n",
        reply_markup=builder.as_markup(),
    )
