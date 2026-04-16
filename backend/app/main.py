from contextlib import asynccontextmanager
from pathlib import Path

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
LANDING_DIR = Path(__file__).resolve().parent.parent.parent / "landing"
if LANDING_DIR.is_dir():
    app.mount("/landing", StaticFiles(directory=str(LANDING_DIR), html=True), name="landing")

    @app.get("/")
    async def root_redirect():
        return FileResponse(LANDING_DIR / "index.html")

