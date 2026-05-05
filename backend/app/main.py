import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, engine
from app.rate_limit import limiter
from app.routers import admin, auth, geocode, health, leads, modules, payments, reports

settings = get_settings()


# ── App logger level + handler ─────────────────────────────────────
# Uvicorn's default log-config setzt nur den `uvicorn`-Logger und seine
# Children (uvicorn.error, uvicorn.access). Der `app`-Hierarchie-Logger
# hat KEINEN Handler attached, und propagation läuft zu Root, der bei
# WARNING bleibt. Effekt: alle `logger.info(...)` Calls in app.* sind
# unsichtbar in stdout (2026-05-04 beim DOI-Mail-Debug selbst erlebt —
# `print(flush=True)` zeigte sich, `logger.info(\"DOI mail sent\")` nicht).
#
# Fix: app-Logger bekommt expliziten StreamHandler auf stderr, level INFO,
# propagate=False damit kein Doppel-Output wenn Root irgendwann Handler
# kriegt. Override per LOG_LEVEL env var.
import sys

_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
_app_logger = logging.getLogger("app")
_app_logger.setLevel(getattr(logging, _log_level, logging.INFO))
if not _app_logger.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _app_logger.addHandler(_h)
    _app_logger.propagate = False


# ── Sentry PII scrubbing ───────────────────────────────────────────
# Redact anything that looks like an email address before an event leaves
# the backend. Lead emails routinely appear in log.exception strings
# (e.g. "Failed to persist Report row for lead_id=X (email=Y)") — with
# LoggingIntegration those strings land in Sentry's message/logentry,
# and we do NOT want Sentry to store subject PII long-term. The regex
# is deliberately tight (only touches the local-part) so stack traces
# stay readable.
_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")


def _scrub_emails(text_value):
    if not isinstance(text_value, str):
        return text_value
    return _EMAIL_RE.sub(r"[email]@\2", text_value)


def _sentry_before_send(event, hint):
    """Walk the event and scrub emails out of message/logentry/extra/tags."""
    try:
        # Main message body of the event
        if "message" in event:
            event["message"] = _scrub_emails(event["message"])
        if "logentry" in event and isinstance(event["logentry"], dict):
            if "message" in event["logentry"]:
                event["logentry"]["message"] = _scrub_emails(event["logentry"]["message"])
            if "formatted" in event["logentry"]:
                event["logentry"]["formatted"] = _scrub_emails(event["logentry"]["formatted"])
        # Exception chain
        for exc in (event.get("exception", {}) or {}).get("values", []) or []:
            if "value" in exc:
                exc["value"] = _scrub_emails(exc["value"])
        # Flat extras + tags
        for key in ("extra", "tags"):
            bag = event.get(key) or {}
            if isinstance(bag, dict):
                for k, v in list(bag.items()):
                    if isinstance(v, str):
                        bag[k] = _scrub_emails(v)
    except Exception:
        # Never let a scrubbing mistake drop a real error report.
        pass
    return event


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
        # PII-Scrubber: keine E-Mails in Sentry-Events
        before_send=_sentry_before_send,
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

    # StaticFiles(html=True) returns Starlette's default JSON 404 for unknown
    # paths — ugly and breaks branding. Subclass to serve landing/404.html
    # with 404 status. /api/* never reaches here (separate routers above).
    class _LandingStaticFiles(StaticFiles):
        async def get_response(self, path, scope):
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code == 404:
                    return FileResponse(LANDING_DIR / "404.html", status_code=404)
                raise

    app.mount("/", _LandingStaticFiles(directory=str(LANDING_DIR), html=True), name="landing")

