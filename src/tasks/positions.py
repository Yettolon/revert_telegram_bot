import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
import uvloop
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from src.celery import celery_app
from src.config import settings
from src.database.models import Position, User, user_positions
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@celery_app.task(name="src.tasks.positions.check_all_positions")
def check_all_positions():
    logger.info("Start checking all positions")

    try:
        # Устанавливаем uvloop как event loop policy
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        # Создаем и запускаем новый event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_check_all_positions())
        finally:
            # Закрываем все соединения перед закрытием loop
            loop.run_until_complete(_cleanup_db())
            loop.close()
    except Exception:
        logger.exception("Ошибка при проверке позиций")
        raise

    logger.info("Cheking all positions completed")


async def _cleanup_db():
    """Закрывает все соединения с БД."""
    from src.database import session as db_session

    if db_session.engine is not None:
        await db_session.engine.dispose()
        logger.info("Database connections closed")


async def _check_all_positions():
    """Асинхронная проверка всех позиций."""
    from src.database import session as db_session

    if db_session.async_session_maker is None:
        await db_session.init_db()
        logger.info("База данных инициализирована в Celery worker")

    async with db_session.async_session_maker() as session:
        try:
            # Загружаем только те позиции, у которых есть хотя бы один активный пользователь
            subquery = (
                select(user_positions.c.position_id)
                .where(user_positions.c.is_active == True)  # noqa
                .distinct()
            )

            result = await session.execute(
                select(Position)
                .where(Position.id.in_(subquery))
                .options(selectinload(Position.users))
            )
            positions = result.scalars().all()

            logger.info(
                f"Найдено позиций для проверки (с активными подписками): {len(positions)}"
            )

            # Проверяем каждую позицию
            for position in positions:
                try:
                    await check_single_position(position, session)
                except Exception as e:
                    logger.error(
                        f"Ошибка при проверке позиции {position.id}: {e}", exc_info=True
                    )

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"Критическая ошибка при проверке позиций: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def check_single_position(position: Position, session):
    """
    Проверяет статус одной позиции и уведомляет пользователей при изменении.

    Args:
        position: Объект позиции
        session: Сессия БД
    """
    logger.info(f"Проверка позиции {position.id} ({position.nft_id})")
    logger.info(
        f"Текущие данные позиции: status={position.is_in_range}, "
        f"price={position.current_price}, min={position.min_price}, max={position.max_price}"
    )

    # Получаем текущий статус и цены из API
    position_data = await fetch_position_data(position.original_url)

    if position_data is None:
        logger.warning(f"Не удалось получить данные для позиции {position.id}")
        return

    new_status = position_data.get("in_range")
    new_current_price = position_data.get("pool_price")
    new_min_price = position_data.get("price_lower")
    new_max_price = position_data.get("price_upper")

    logger.info(
        f"Новые данные из API: status={new_status}, "
        f"price={new_current_price}, min={new_min_price}, max={new_max_price}"
    )

    # Сохраняем старые значения для уведомления
    old_status = position.is_in_range
    old_current_price = position.current_price

    # Обновляем данные позиции
    position.is_in_range = new_status
    if new_current_price is not None:
        position.current_price = new_current_price
    if new_min_price is not None:
        position.min_price = new_min_price
    if new_max_price is not None:
        position.max_price = new_max_price

    await session.flush()
    await session.refresh(position)

    # Если статус изменился - отправляем уведомления
    if new_status != old_status:
        logger.info(
            f"Позиция {position.id} изменила статус: {old_status} -> {new_status}"
        )

        # Получаем только активных пользователей для этой позиции
        result = await session.execute(
            select(User.telegram_id)
            .select_from(user_positions)
            .join(User, User.id == user_positions.c.user_id)
            .where(
                and_(
                    user_positions.c.position_id == position.id,
                    user_positions.c.is_active == True,  # noqa
                )
            )
        )
        active_user_ids = [row[0] for row in result.all()]

        if active_user_ids:
            logger.info(
                f"Найдено {len(active_user_ids)} активных подписчиков для позиции {position.id}"
            )

            # Формируем данные для уведомления
            notification_data = {
                "position_id": position.id,
                "exchange": position.exchange.value,
                "network": position.network.value,
                "nft_id": position.nft_id,
                "token_1_symbol": position.token_1_symbol,
                "token_2_symbol": position.token_2_symbol,
                "new_status": new_status,
                "old_status": old_status,
                "current_price": new_current_price,
                "old_price": old_current_price,
                "min_price": new_min_price,
                "max_price": new_max_price,
            }

            notify_users_position_changed.delay(active_user_ids, notification_data)
        else:
            logger.info(f"Нет активных подписчиков для позиции {position.id}")
    else:
        logger.debug(f"Позиция {position.id} не изменила статус, обновлены только цены")


async def fetch_position_data(url: str) -> Optional[Dict[str, Any]]:
    """
    Получает данные позиции из Revert API.

    Args:
        url: URL позиции в Revert API

    Returns:
        Dict с данными позиции или None при ошибке
    """
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as http_session:
            async with http_session.get(url) as resp:
                resp.raise_for_status()
                result = await resp.json()

                if not (result.get("success") and result.get("data")):
                    logger.warning(f"Некорректный ответ от API для {url}")
                    return None

                data = result["data"]
                position_data = {
                    "in_range": bool(data.get("in_range", False)),
                    "pool_price": (
                        float(data.get("pool_price"))
                        if data.get("pool_price")
                        else None
                    ),
                    "price_lower": (
                        float(data.get("price_lower"))
                        if data.get("price_lower")
                        else None
                    ),
                    "price_upper": (
                        float(data.get("price_upper"))
                        if data.get("price_upper")
                        else None
                    ),
                }

                logger.debug(f"Данные позиции {url}: {position_data}")
                return position_data

    except aiohttp.ClientError as e:
        logger.error(f"Ошибка при запросе к API {url}: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Таймаут при запросе к API {url}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке {url}: {e}", exc_info=True)
        return None


@celery_app.task(name="src.tasks.positions.notify_users_position_changed")
def notify_users_position_changed(user_telegram_ids, notification_data):
    """Отправляет уведомления пользователям об изменении позиции."""
    try:
        # Устанавливаем uvloop как event loop policy
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        # Создаем и запускаем новый event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_notify_users(user_telegram_ids, notification_data))
        finally:
            loop.close()
    except Exception:
        logger.exception("Ошибка при отправке уведомлений")
        raise


async def _notify_users(
    user_telegram_ids: List[int], notification_data: Dict[str, Any]
):
    """Асинхронная отправка уведомлений."""
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    # Извлекаем данные
    new_status = notification_data.get("new_status")
    old_status = notification_data.get("old_status")
    current_price = notification_data.get("current_price")
    old_price = notification_data.get("old_price")
    min_price = notification_data.get("min_price")
    max_price = notification_data.get("max_price")
    token_1 = notification_data.get("token_1_symbol", "?")
    token_2 = notification_data.get("token_2_symbol", "?")
    exchange = notification_data.get("exchange")
    network = notification_data.get("network")
    nft_id = notification_data.get("nft_id")

    # Формируем сообщение
    status_emoji = "🟢" if new_status else "🔴"
    status_text = "In range" if new_status else "Out of range"

    # Определяем направление изменения
    if not new_status and old_status:
        # Вышла из диапазона
        if current_price and min_price and max_price:
            if current_price < min_price:
                boundary_info = f"\n\n⬇️ Price dropped below minimum\nMin price: <code>{min_price:.6f}</code>"
            elif current_price > max_price:
                boundary_info = f"\n\n⬆️ Price rose above maximum\nMax price: <code>{max_price:.6f}</code>"
            else:
                boundary_info = ""
        else:
            boundary_info = ""
    elif new_status and not old_status:
        # Вернулась в диапазон
        boundary_info = "\n\n✅ Price returned to range"
    else:
        boundary_info = ""

    # Добавляем информацию о ценах
    price_info = ""
    if current_price is not None:
        price_info += f"\n\n💰 Current price: <code>{current_price:.6f}</code>"
        if old_price and old_price != current_price:
            change = ((current_price - old_price) / old_price) * 100
            change_emoji = "📈" if change > 0 else "📉"
            price_info += f"\n{change_emoji} Change: {change:+.2f}%"

    if min_price is not None and max_price is not None:
        price_info += f"\n\n📊 Price range:"
        price_info += f"\nMin: <code>{min_price:.6f}</code>"
        price_info += f"\nMax: <code>{max_price:.6f}</code>"

    message = (
        f"{status_emoji} <b>Position status update!</b>\n\n"
        f"<b>{token_1}/{token_2}</b>\n"
        f"Exchange: {exchange}\n"
        f"Network: {network}\n"
        f"NFT ID: <code>{nft_id}</code>\n\n"
        f"Status: <b>{status_text}</b>"
        f"{boundary_info}"
        f"{price_info}"
    )

    # Отправляем уведомления
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        success_count = 0
        for telegram_id in user_telegram_ids:
            try:
                await bot.send_message(telegram_id, message)
                success_count += 1
                logger.info(f"Уведомление отправлено пользователю {telegram_id}")
                # Небольшая задержка между отправками
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(
                    f"Ошибка отправки уведомления пользователю {telegram_id}: {e}"
                )

        logger.info(f"Уведомления отправлены: {success_count}/{len(user_telegram_ids)}")
    finally:
        await bot.session.close()
