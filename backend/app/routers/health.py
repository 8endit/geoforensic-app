"""Health check endpoint."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])
settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)

