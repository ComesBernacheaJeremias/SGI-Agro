"""Configuración leída de variables de entorno (.env). Único lugar donde se leen."""

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    environment: Literal["development", "test", "production"] = "development"

    postgres_user: str
    postgres_password: str
    postgres_db: str
    db_host: str = "db"
    db_port: int = 5432

    jwt_secret: str
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    login_max_attempts: int = 5
    login_lock_minutes: int = 15

    timezone: str = "America/Argentina/Buenos_Aires"

    # Errores a Sentry (opcional: vacío = desactivado)
    sentry_dsn: str = ""
    app_version: str = "dev"

    def database_url(self, *, test: bool = False) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.db_host,
            port=self.db_port,
            database=f"{self.postgres_db}_test" if test else self.postgres_db,
        )

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # los valores vienen de las variables de entorno
