import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.email_service import send_report_email
from app.full_report import generate_full_report
from app.models import Lead
from app.soil_data import SoilDataLoader
from app.rate_limit import limiter
from app.routers.reports import geocode_address

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)


class LeadCreate(BaseModel):
    email: EmailStr
    address: str | None = None
    answers: dict | None = None
    timestamp: str | None = None
    source: str = "quiz"


class LeadResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


def _ampel_from_velocity(abs_velocity: float) -> tuple[str, int]:
    if abs_velocity < 2:
        return "gruen", 85
    if abs_velocity <= 5:
        return "gelb", 60
    return "rot", 30


async def _generate_and_send_lead_report(
    email: str,
    address: str,
    answers: dict,
    db_url: str,
) -> None:
    """Background task: geocode → EGMS query → PDF → email."""
    from app.database import SessionLocal

    try:
        # 1. Geocode
        lat, lon, display_name, country_code = await geocode_address(address)

        # 2. EGMS query
        async with SessionLocal() as db:
            result = await db.execute(
                text(
                    """
                    SELECT
                        mean_velocity_mm_yr,
                        ST_Distance(
                            geom::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                        ) AS distance_m
                    FROM egms_points
                    WHERE ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        500
                    )
                    ORDER BY distance_m ASC
                    """
                ),
                {"lat": lat, "lon": lon},
            )
            points = [dict(row._mapping) for row in result]

        # 3. Compute metrics
        if points:
            velocities = [abs(float(p["mean_velocity_mm_yr"])) for p in points]
            mean_v = sum(velocities) / len(velocities)
            max_v = max(velocities)
            ampel, geo_score = _ampel_from_velocity(mean_v)
        else:
            mean_v, max_v, ampel, geo_score = 0.0, 0.0, "gruen", None

        # 4. Query soil data (SoilGrids + LUCAS + CORINE)
        try:
            soil_loader = SoilDataLoader.get()
            soil_profile = soil_loader.query_full_profile(lat, lon)
        except Exception:
            logger.warning("Soil data query failed for (%s, %s), using empty profile", lat, lon)
            soil_profile = {}

        # 5. Generate full PDF
        pdf_bytes = generate_full_report(
            address=display_name,
            lat=lat,
            lon=lon,
            ampel=ampel,
            point_count=len(points),
            mean_velocity=mean_v,
            max_velocity=max_v,
            geo_score=geo_score,
            soil_profile=soil_profile,
            answers=answers or {},
        )

        # 6. Send email
        await send_report_email(
            recipient_email=email,
            report_address=display_name,
            pdf_bytes=pdf_bytes,
            report_id=f"lead-{email}",
        )
        logger.info("Lead report sent to %s for address %s (%s, %d pts)", email, address, ampel, len(points))

    except Exception:
        logger.exception("Failed to generate lead report for %s", email)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/hour")
async def capture_lead(
    request: Request,
    payload: LeadCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    lead = Lead(
        email=payload.email,
        quiz_answers=payload.answers,
        source=payload.source,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # If address provided, generate and send personalized report in background
    if payload.address and payload.address.strip():
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=payload.email,
            address=payload.address.strip(),
            answers=payload.answers or {},
            db_url="",  # uses SessionLocal directly
        )

    return LeadResponse(
        id=str(lead.id),
        email=lead.email,
        created_at=lead.created_at,
    )
