from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "geoforensic-api"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/geoforensic"
    secret_key: str = Field(default="change-me", min_length=8)
    access_token_expire_minutes: int = 60 * 24
    jwt_algorithm: str = "HS256"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://geoforensic.de",
        "https://uninducible-myrtle-unsecluded.ngrok-free.dev",
    ]

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_checkout_success_url: str = "http://localhost:3000/dashboard?paid=1"
    stripe_checkout_cancel_url: str = "http://localhost:3000/dashboard?paid=0"
    stripe_report_price_cents: int = 19900


@lru_cache
def get_settings() -> Settings:
    return Settings()

