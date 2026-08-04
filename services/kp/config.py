from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Bit_micro_serverse — kp-service"
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "*"

    POSTGRES_USER: str = "bitserves"
    POSTGRES_PASSWORD: str = "bitserves_password"
    POSTGRES_DB_KP: str = "kp_db"
    POSTGRES_HOST_KP: str = "localhost"
    POSTGRES_PORT: int = 5432

    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST_KP}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_KP}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
