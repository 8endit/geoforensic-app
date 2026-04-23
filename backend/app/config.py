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
        "http://localhost:8000",
        "https://geoforensic.de",
        "https://www.geoforensic.de",
        "https://bodenbericht.de",
        "https://www.bodenbericht.de",
    ]
    # systeme.io subdomains via allow_origin_regex in main.py

    # Public base URL for download links in emails
    public_base_url: str = "https://geoforensic.de"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_checkout_success_url: str = "http://localhost:3000/dashboard?paid=1"
    stripe_checkout_cancel_url: str = "http://localhost:3000/dashboard?paid=0"
    stripe_report_price_cents: int = 19900

    google_client_id: str = ""
    apple_client_id: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "bericht@geoforensic.de"
    smtp_from_name: str = "Bodenbericht"

    # EGMS screening — used by the pipeline (SQL radius) and by the report
    # template so the radius + measurement window is not hardcoded in copy.
    egms_radius_m: int = 500
    egms_period_start: int = 2019
    egms_period_end: int = 2023

    # Operator metadata shown in the PDF footer + legal pages
    operator_legal_name: str = "Tepnosholding GmbH"
    operator_imprint_url: str = "https://bodenbericht.de/impressum.html"


@lru_cache
def get_settings() -> Settings:
    return Settings()

