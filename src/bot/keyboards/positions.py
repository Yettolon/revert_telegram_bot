from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.enums import ExchangeEnum, NetworkEnum
from src.database.models import Position


def get_positions_keyboard(
    rows: list[tuple[Position, bool]],
) -> InlineKeyboardMarkup:
    """
    Keyboard for 'My positions':
    - List of user positions (with notification status)
    - Add position button
    """
    builder = InlineKeyboardBuilder()

    for pos, is_active in rows:
        notify_emoji = "🔔" if is_active else "🔕"

        builder.row(
            InlineKeyboardButton(
                text=(
                    f"{notify_emoji} "
                    f"{pos.exchange.value} / "
                    f"{pos.network.value} / NFT {pos.nft_id}"
                ),
                callback_data=f"position_{pos.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="➕ Add Position",
            callback_data="positions_add",
        )
    )

    return builder.as_markup()


def get_add_position_method_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура после нажатия 'Добавить позицию'
    с выбором метода: по URL или вручную
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🌐 Add via revert.finance URL",
            callback_data="add_position_url",
        )
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Add manually", callback_data="add_position_manual")
    )

    return builder.as_markup()


def get_exchange_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ex in ExchangeEnum:
        builder.row(
            InlineKeyboardButton(text=ex.value, callback_data=f"exchange_{ex.value}")
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="add_position_cancel")
    )
    return builder.as_markup()


def get_network_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for net in NetworkEnum:
        builder.row(
            InlineKeyboardButton(text=net.value, callback_data=f"network_{net.value}")
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="add_position_cancel")
    )
    return builder.as_markup()
