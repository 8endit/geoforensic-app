"""Async SQLAlchemy database engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
# Pool sizing für Multi-Worker uvicorn (--workers 4): jeder Worker hat
# einen eigenen Engine-Instance + eigenen Pool. Mit pool_size=8 +
# max_overflow=12 = 4 × 20 = 80 max Connections, Postgres default ist
# max_connections=100. Pre-ping testet Connection vor jedem Checkout
# (verhindert "stale connection" nach DB-Restarts), recycle=300 schließt
# Connections nach 5 Min Leerlauf weg damit kein TCP-Idle-Timeout vom
# Container-Network sie hinter unserem Rücken killt.
engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=settings.debug,
    pool_size=8,
    max_overflow=12,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

