from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Bit_micro_serverse — auth-service"
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "*"

    HEAD_REGISTER_PASSWORD: str = "123456789"

    INTERNAL_API_TOKEN: str = "change-me-internal-token"

    PASSWORD_RESET_CODE_TTL_MINUTES: int = 15

    # SMTP для отправки писем (сброс пароля). Если SMTP_HOST пуст — dev-режим: код пишется в консоль.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Бит.Serves"
    SMTP_USE_SSL: bool = True  # True = SSL (порт 465), False = STARTTLS (порт 587)

    POSTGRES_USER: str = "bitserves"
    POSTGRES_PASSWORD: str = "bitserves_password"
    POSTGRES_DB_AUTH: str = "auth_db"
    POSTGRES_HOST_AUTH: str = "localhost"
    POSTGRES_PORT: int = 5432

    DATABASE_URL_OVERRIDE: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def DATABASE_URL(self) -> str:
        return self.DATABASE_URL_OVERRIDE or (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST_AUTH}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_AUTH}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()