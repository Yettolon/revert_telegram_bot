import aiohttp
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bot.keyboards.positions import (
    get_add_position_method_keyboard,
    get_exchange_keyboard,
    get_network_keyboard,
    get_positions_keyboard,
)
from src.bot.states.positions import AddPositionStates
from src.bot.tools import parse_revert_position_url
from src.config import settings
from src.database.models import Position, User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Создаём роутер для этого модуля
router = Router(name="positions")


@router.message(lambda message: message.text == "📊 Мои позиции")
async def positions_handler(message: Message, user: User, session: AsyncSession):
    result = await session.execute(
        select(Position).join(Position.users).where(User.id == user.id)
    )
    positions = result.scalars().all()

    if not positions:
        await message.answer(
            "У вас пока нет позиций.",
            reply_markup=get_positions_keyboard([]),  # передаем пустой список
        )
        return

    await message.answer(
        "Ваши позиции:", reply_markup=get_positions_keyboard(positions)
    )


# Обработчик деталей позиции
@router.callback_query(lambda c: c.data.startswith("position_"))
async def position_detail(callback: CallbackQuery, session: AsyncSession):
    position_id = int(callback.data.split("_")[1])
    result = await session.execute(select(Position).where(Position.id == position_id))
    position = result.scalar_one_or_none()

    if not position:
        await callback.message.answer("Позиция не найдена.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()

    if position.owner_address:
        builder.row(
            InlineKeyboardButton(
                text="🔎 Посмотреть в Debank",
                url=f"{settings.DEBANK_PROFILE_URL}{position.owner_address}",
            )
        )

    # Кнопка удалить позицию
    builder.row(
        InlineKeyboardButton(
            text="❌ Удалить позицию", callback_data=f"delete_position_{position.id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к позициям", callback_data="positions_back")
    )

    await callback.message.answer(
        f"Детали позиции:\n"
        f"Exchange: {position.exchange.value}\n"
        f"Network: {position.network.value}\n"
        f"NFT ID позиции: {position.nft_id}",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("delete_position_"))
async def delete_position(callback: CallbackQuery, session: AsyncSession, user: User):

    position_id = int(callback.data.split("_")[2])

    # Получаем позицию с пользователями
    result = await session.execute(
        select(Position)
        .where(Position.id == position_id)
        .options(selectinload(Position.users))
    )
    position = result.scalar_one_or_none()

    if not position:
        await callback.message.answer("Позиция не найдена.")
        await callback.answer()
        return

    # Удаляем связь текущего пользователя с позицией
    if user in position.users:
        position.users.remove(user)

    # Если после удаления пользователей нет, удаляем саму позицию
    if not position.users:
        await session.delete(position)

    await session.commit()
    await callback.message.answer("Позиция удалена.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "positions_add")
async def add_position_callback(callback: CallbackQuery):
    await callback.message.answer(
        "Выберите метод добавления позиции:",
        reply_markup=get_add_position_method_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "add_position_manual")
async def manual_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Выберите Exchange:", reply_markup=get_exchange_keyboard()
    )
    await state.set_state(AddPositionStates.choosing_exchange)
    await callback.answer()


@router.callback_query(
    lambda c: c.data.startswith("exchange_"),
    StateFilter(AddPositionStates.choosing_exchange),
)
async def choose_exchange(callback: CallbackQuery, state: FSMContext):
    exchange = callback.data.split("exchange_")[1]
    await state.update_data(exchange=exchange)

    # Переходим к выбору сети
    await callback.message.answer(
        "Выберите Network:", reply_markup=get_network_keyboard()
    )
    await state.set_state(AddPositionStates.choosing_network)  # <- важно!
    await callback.answer()


@router.callback_query(
    lambda c: c.data.startswith("network_"),
    StateFilter(AddPositionStates.choosing_network),
)
async def choose_network(callback: CallbackQuery, state: FSMContext):
    network = callback.data.split("network_")[1]
    await state.update_data(network=network)

    await callback.message.answer("Введите ID позиции (NFT):")
    await state.set_state(AddPositionStates.entering_position_id)
    await callback.answer()


@router.message(StateFilter(AddPositionStates.entering_position_id))
async def enter_position_id(
    message: Message, state: FSMContext, session: AsyncSession, user: User
):
    nft_id = message.text.strip()
    data = await state.get_data()

    exchange = data.get("exchange")
    network = data.get("network")

    url = f"{settings.REVERT_API_URL}/v1/positions/{network}/{exchange}/{nft_id}"

    async with aiohttp.ClientSession() as http_session:
        async with http_session.get(url, timeout=10) as resp:
            try:
                resp.raise_for_status()
                result = await resp.json()
            except Exception:
                await message.answer(
                    "Ошибка при обращении к Revert API. Попробуйте позже."
                )
                return

    # Проверяем, что данные валидные
    if not (result.get("success") and result.get("data")):
        await message.answer("Позиция не найдена в Revert API.")
        return

    data_resp = result["data"]
    if str(data_resp.get("nft_id")) != nft_id:
        await message.answer("Позиция не найдена или ID не совпадает.")
        return

    # Проверяем, есть ли уже такая позиция в базе
    result = await session.execute(
        select(Position)
        .where(
            Position.exchange == exchange,
            Position.network == network,
            Position.nft_id == nft_id,
        )
        .options(selectinload(Position.users))
    )
    position = result.scalar_one_or_none()

    tokens = list(data_resp.get("tokens", {}).values())
    token_1 = tokens[0] if len(tokens) > 0 else {}
    token_2 = tokens[1] if len(tokens) > 1 else {}
    owner = data_resp.get("owner")

    if position:
        # Если позиция уже есть — добавляем пользователя в M2M
        if user not in position.users:
            position.users.append(user)
            await session.commit()
        status = (
            "🟢 <b>In range</b>" if position.is_in_range else "🔴 <b>Out of range</b>"
        )
        await message.answer(
            f"Вы подписаны на существующую позицию:\n"
            f"{status}\n"
            f"Tokens: {position.token_1_symbol}/{position.token_2_symbol}\n"
            f"Exchange: {position.exchange.value}\n"
            f"Network: {position.network.value}\n"
            f"NFT ID позиции: {position.nft_id}\n"
        )
    else:
        # Если позиции нет — создаем новую и добавляем пользователя
        new_position = Position(
            exchange=exchange,
            network=network,
            nft_id=nft_id,
            original_url=url,
            token_1_symbol=token_1.get("symbol"),
            token_1_address=token_1.get("address"),
            token_2_symbol=token_2.get("symbol"),
            token_2_address=token_2.get("address"),
            owner_address=owner,
            users=[user],  # сразу M2M связь
        )
        session.add(new_position)
        await session.commit()

        status = (
            "🟢 <b>In range</b>"
            if new_position.is_in_range
            else "🔴 <b>Out of range</b>"
        )
        await message.answer(
            f"Новая позиция добавлена:\n"
            f"{status}\n"
            f"Tokens: {new_position.token_1_symbol}/{new_position.token_2_symbol}\n"
            f"Exchange: {exchange}\n"
            f"Network: {network}\n"
            f"NFT ID позиции: {nft_id}\n"
        )

    await state.clear()


@router.callback_query(lambda c: c.data == "add_position_cancel")
async def cancel_add_position(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Добавление позиции отменено.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "add_position_url")
async def add_by_url(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddPositionStates.entering_url)
    await callback.message.answer("Введите ссылку на позицию с revert.finance")
    await callback.answer()


@router.message(StateFilter(AddPositionStates.entering_url))
async def add_position_by_url(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
):
    try:
        exchange, network, nft_id = parse_revert_position_url(message.text.strip())
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return

    url = f"{settings.REVERT_API_URL}/v1/positions/{network.value}/{exchange.value}/{nft_id}"

    async with aiohttp.ClientSession() as http_session:
        async with http_session.get(url, timeout=10) as resp:
            try:
                resp.raise_for_status()
                result = await resp.json()
            except Exception:
                await message.answer(
                    "Ошибка при обращении к Revert API. Попробуйте позже."
                )
                return

    if not (result.get("success") and result.get("data")):
        await message.answer("Позиция не найдена в Revert API.")
        return

    data_resp = result["data"]
    if str(data_resp.get("nft_id")) != nft_id:
        await message.answer("Позиция не найдена или ID не совпадает.")
        return

    tokens = list(data_resp.get("tokens", {}).values())
    token_1 = tokens[0] if len(tokens) > 0 else {}
    token_2 = tokens[1] if len(tokens) > 1 else {}
    owner = data_resp.get("owner")

    # Проверяем, есть ли уже такая позиция в базе
    result = await session.execute(
        select(Position)
        .where(
            Position.exchange == exchange,
            Position.network == network,
            Position.nft_id == nft_id,
        )
        .options(selectinload(Position.users))
    )
    position = result.scalar_one_or_none()

    if position:
        # Если позиция уже есть — добавляем пользователя в M2M
        if user not in position.users:
            position.users.append(user)
            await session.commit()
        status = (
            "🟢 <b>In range</b>" if position.is_in_range else "🔴 <b>Out of range</b>"
        )
        await message.answer(
            f"Вы подписаны на существующую позицию:\n"
            f"{status}\n"
            f"Tokens: {position.token_1_symbol}/{position.token_2_symbol}\n"
            f"Exchange: {position.exchange.value}\n"
            f"Network: {position.network.value}\n"
            f"ID позиции: {position.nft_id}\n"
        )
    else:
        # Если позиции нет — создаем новую и добавляем пользователя
        new_position = Position(
            exchange=exchange,
            network=network,
            nft_id=nft_id,
            original_url=url,
            token_1_symbol=token_1.get("symbol"),
            token_1_address=token_1.get("address"),
            token_2_symbol=token_2.get("symbol"),
            token_2_address=token_2.get("address"),
            owner_address=owner,
            users=[user],  # M2M связь
        )
        session.add(new_position)
        await session.commit()

        status = (
            "🟢 <b>In range</b>"
            if new_position.is_in_range
            else "🔴 <b>Out of range</b>"
        )
        await message.answer(
            f"Новая позиция добавлена:\n"
            f"{status}\n"
            f"Tokens: {new_position.token_1_symbol}/{new_position.token_2_symbol}\n"
            f"Exchange: {exchange.value}\n"
            f"Network: {network.value}\n"
            f"ID позиции: {nft_id}\n"
        )

    await state.clear()
