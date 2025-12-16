import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Настройка и получение логгера для модуля.

    Args:
        name: Имя логгера (обычно __name__ модуля)

    Returns:
        logging.Logger: Настроенный экземпляр логгера
    """
    logger = logging.getLogger(name)

    # Если у логгера уже есть обработчики, не добавляем новые
    if logger.handlers:
        return logger

    # Устанавливаем уровень логирования
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Создаем форматтер
    formatter = logging.Formatter(fmt=settings.LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Обработчик для записи в файл (если не в Docker, или если указана папка logs)
    logs_dir = Path("logs")
    if logs_dir.exists() or not Path("/.dockerenv").exists():
        logs_dir.mkdir(exist_ok=True)

        # Общий лог файл
        file_handler = RotatingFileHandler(
            logs_dir / "bot.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Отдельный файл для ошибок
        error_handler = RotatingFileHandler(
            logs_dir / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    # Предотвращаем дублирование логов в родительских логгерах
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить существующий логгер или создать новый.

    Args:
        name: Имя логгера

    Returns:
        logging.Logger: Экземпляр логгера
    """
    return setup_logger(name)


# Настройка логирования для сторонних библиотек
def configure_third_party_loggers() -> None:
    """
    Настройка уровней логирования для сторонних библиотек.
    Уменьшает verbose вывод от aiogram, aiohttp и других.
    """
    # Aiogram
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    # Aiohttp
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    # SQLAlchemy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # Asyncpg
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


# Инициализация при импорте модуля
configure_third_party_loggers()
