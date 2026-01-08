from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Telegram Bot
    BOT_TOKEN: str = Field(..., description="Токен телеграм бота")
    ADMIN_IDS: list[int] = Field(
        default_factory=list, description="ID администраторов бота"
    )

    # Database
    DB_HOST: str = Field(default="localhost", description="Хост базы данных")
    DB_PORT: int = Field(default=5432, description="Порт базы данных")
    DB_NAME: str = Field(default="revert_bot", description="Имя базы данных")
    DB_USER: str = Field(default="bot_user", description="Пользователь БД")
    DB_PASSWORD: str = Field(..., description="Пароль БД")

    # Revert Finance API
    REVERT_API_URL: str = Field(
        default="https://api.revert.finance", description="URL Revert Finance API"
    )
    REVERT_API_KEY: str | None = Field(
        default=None, description="API ключ Revert Finance (если требуется)"
    )

    # Debank
    DEBANK_PROFILE_URL: str = Field(
        default="https://debank.com/profile/", description="Debank profile url"
    )

    # Scheduler
    UPDATE_INTERVAL: int = Field(
        default=300, description="Интервал обновления данных в секундах"
    )
    NOTIFICATION_CHECK_INTERVAL: int = Field(
        default=60, description="Интервал проверки уведомлений в секундах"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Формат логов",
    )

    # Application
    DEBUG: bool = Field(default=False, description="Режим отладки")

    REDIS_URL: str = Field(default="redis://redis:6379/0")

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list[int]) -> list[int]:
        """Парсинг ADMIN_IDS из строки или списка."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @property
    def database_url(self) -> str:
        """Формирование DATABASE_URL для asyncpg."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """Формирование DATABASE_URL для синхронных операций (миграции)."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


# Создание экземпляра настроек
settings = Settings()
