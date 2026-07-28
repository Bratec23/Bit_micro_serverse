from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Bit_micro_serverse — auth-service"
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "*"

    HEAD_REGISTER_PASSWORD: str = "123456789"

    PASSWORD_RESET_CODE_TTL_MINUTES: int = 15

    POSTGRES_USER: str = "bitserves"
    POSTGRES_PASSWORD: str = "bitserves_password"
    POSTGRES_DB_AUTH: str = "auth_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def DATABASE_URL(self) -> str:
        if self.POSTGRES_HOST == "localhost":
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_AUTH}"
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_AUTH}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()