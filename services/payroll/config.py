from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Bit_micro_serverse — payroll-service"
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "*"

    INTERNAL_API_TOKEN: str = "change-me-internal-token"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"

    VAT_RATE_PERCENT: float = 5.0

    POSTGRES_USER: str = "bitserves"
    POSTGRES_PASSWORD: str = "bitserves_password"
    POSTGRES_DB_PAYROLL: str = "payroll_db"
    POSTGRES_HOST_PAYROLL: str = "localhost"
    POSTGRES_PORT: int = 5432

    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST_PAYROLL}:{self.POSTGRES_PORT}/{self.POSTGRES_DB_PAYROLL}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
