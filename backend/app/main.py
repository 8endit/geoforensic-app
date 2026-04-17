import os
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, engine
from app.rate_limit import limiter
from app.routers import admin, auth, geocode, health, leads, modules, payments, reports

settings = get_settings()

# Sentry-Init muss vor FastAPI-App-Creation passieren, damit die FastAPI-Integration
# alle Request-Lifecycles erfassen kann. Wenn SENTRY_DSN nicht gesetzt ist (z.B.
# lokal), ist Sentry no-op — sdk wirft keinen Fehler, schickt nur nichts.
_sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("SENTRY_RELEASE") or None,
        # 10 % aller Requests als Performance-Trace, reicht fuer MVP
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        # Keine personenbezogenen Daten (IP, User-ID) automatisch mitsenden
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        # MVP bootstrap: creates tables if they don't exist.
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.systeme\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(geocode.router)
app.include_router(leads.router)
app.include_router(modules.router)
app.include_router(reports.router)
app.include_router(payments.router)
app.include_router(health.router)

# ── Static landing pages ────────────────────────────────────────────
# In Docker: /app/landing (volume mount). Local dev: ../../landing relative to backend/app/main.py
# Mounted at "/" so relative paths in HTML work the same locally and in production
# (e.g. /muster-bericht.html, /quiz.html, /datenquellen.html). All API routes live
# under /api/... so there is no collision.
_here = Path(__file__).resolve().parent
LANDING_DIR = _here.parent / "landing"  # /app/landing in Docker
if not LANDING_DIR.is_dir():
    LANDING_DIR = _here.parent.parent / "landing"  # local dev fallback
if LANDING_DIR.is_dir():
    @app.get("/admin")
    async def admin_dashboard():
        return FileResponse(LANDING_DIR / "admin.html")

    app.mount("/", StaticFiles(directory=str(LANDING_DIR), html=True), name="landing")

