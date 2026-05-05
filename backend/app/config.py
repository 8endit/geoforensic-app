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
    # Bundle-Tiers (Modell B): Basis = 12 Hauptsektionen + EU-Directive,
    # Komplett = Basis + 5 Bonus-Module (Wind-Erosion separat, PAK/PCB,
    # mikrobielle Aktivität, Bodenstruktur, Hydromorphologie). EARLY50
    # wirkt prozentual auf beide → Basis 19,50 € / Komplett 29,50 €.
    stripe_report_price_cents: int = 3900       # Basis (kept name for backwards compat)
    stripe_report_komplett_price_cents: int = 5900  # Komplett-Tier

    # Operator's own email — used to exclude internal smoke-test leads
    # from the EARLY50 coupon counter so launch-day promo slots aren't
    # burned by your own QA runs. Set in backend/.env.
    operator_email: str = "benjaminweise41@gmail.com"

    google_client_id: str = ""
    apple_client_id: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "bericht@bodenbericht.de"
    smtp_from_name: str = "Bodenbericht"

    # Provenexpert-Review-Link für die Follow-up-Mail nach PDF-Versand.
    # Leer lassen → keine Review-Mail wird verschickt (Domenico-Sprint
    # B.5 wartet noch auf Profil-Anlage). Sobald Profil existiert und URL
    # eingetragen ist, schickt scripts/send_pending_review_requests.py
    # die Bitte an alle Reports älter als REVIEW_REQUEST_DELAY_DAYS.
    provenexpert_review_url: str = ""
    review_request_delay_days: int = 7

    # EGMS screening — used by the pipeline (SQL radius) and by the report
    # template so the radius + measurement window is not hardcoded in copy.
    #
    # Wir bleiben bei 500 m als Fenster (typisch ~50-80 PSI in DE-Stadt)
    # und gewichten den Mittelwert ÜBER das Fenster mit inverser Distanz
    # (1/d, 50 m-Floor; siehe routers/leads.py + routers/reports.py).
    # Damit dominieren Punkte direkt am Haus die Ampel, statt von
    # Nachbarblöcken 400 m weiter weg verwässert zu werden. Größerer
    # Radius wäre nur eine Volumen-Schein-Verbesserung.
    egms_radius_m: int = 500
    egms_period_start: int = 2019
    egms_period_end: int = 2023

    # Operator metadata shown in the PDF footer + legal pages
    operator_legal_name: str = "Tepnosholding GmbH"
    operator_imprint_url: str = "https://bodenbericht.de/impressum.html"

    # Redis-backed Nominatim response cache. Empty URL disables the cache
    # entirely (graceful fallback, the pipeline keeps working against the
    # live Nominatim API). TTL ist 7 Tage (vorher 30): OSM ist editierbar
    # und Vandalismus (z.B. "Berlin" → "Nazi-Stadt", echter Vorfall
    # 2026-05-05) bleibt sonst einen Monat in unserem Cache stecken,
    # selbst wenn OSM ihn binnen Stunden revertiert. 7 Tage ist immer
    # noch lang genug um Nominatim's 1 req/s Rate-Limit zu respektieren
    # und gibt uns max 1 Woche Schaden statt 1 Monat. Defense gegen
    # vergiftete Reads + Writes liegt zusätzlich in routers/reports.py
    # (_contains_vandalism guard).
    redis_url: str = ""
    geocode_cache_ttl_seconds: int = 7 * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

