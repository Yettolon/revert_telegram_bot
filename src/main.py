import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.handlers import admin, positions
from src.bot.handlers import settings as settings_router
from src.bot.handlers import start
from src.bot.middlewares.database import UserSessionMiddleware
from src.config import settings
from src.database.session import close_db, init_db
from src.utils.logger import setup_logger

# Настройка логирования
logger = setup_logger(__name__)


async def on_startup(bot: Bot) -> None:
    """
    Действия при запуске бота.

    Args:
        bot: Экземпляр бота
    """
    logger.info("Запуск бота...")

    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")

    # Уведомление администраторов о запуске
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 Бот запущен и готов к работе!")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    logger.info("Бот успешно запущен")


async def on_shutdown(bot: Bot) -> None:
    """
    Действия при остановке бота.

    Args:
        bot: Экземпляр бота
    """
    logger.info("Остановка бота...")

    # Уведомление администраторов об остановке
    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🛑 Бот остановлен")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    # Закрытие соединений с БД
    await close_db()
    logger.info("Соединения с базой данных закрыты")

    logger.info("Бот остановлен")


def register_handlers(dp: Dispatcher) -> None:
    """
    Регистрация всех обработчиков команд и сообщений.

    Args:
        dp: Диспетчер aiogram
    """
    # Регистрация роутеров из модулей
    dp.include_router(start.router)
    dp.include_router(positions.router)
    dp.include_router(settings_router.router)
    dp.include_router(admin.router)

    logger.info("Обработчики зарегистрированы")


def register_middlewares(dp: Dispatcher) -> None:
    """
    Регистрация middleware.

    Args:
        dp: Диспетчер aiogram
    """
    # Middleware для работы с БД и автоматической загрузки пользователя
    dp.update.middleware(UserSessionMiddleware())

    logger.info("Middleware зарегистрированы")


async def main() -> None:
    """
    Основная функция приложения.
    Создает бота, диспетчер и запускает polling.
    """
    try:
        # Инициализация бота
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        # Инициализация диспетчера
        dp = Dispatcher()

        # Регистрация компонентов
        register_middlewares(dp)
        register_handlers(dp)

        # Регистрация startup и shutdown хуков
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        raise

    finally:
        # Закрытие сессии бота
        await bot.session.close()
        logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    try:
        # Запуск приложения
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Необработанное исключение: {e}", exc_info=True)
