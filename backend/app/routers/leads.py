"""Lead capture endpoint — quiz/landing form -> geocode -> full report -> email."""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.email_service import send_report_email
from app.html_report import generate_html_report
from app.models import Lead
from app.pdf_renderer import html_to_pdf
from app.rate_limit import limiter
from app.routers.reports import geocode_address
from app.soil_data import SoilDataLoader

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
    geocoded: tuple[float, float, str, str] | None = None,
) -> None:
    """Background task: geocode → EGMS query → PDF → email.

    Accepts pre-computed geocode (lat, lon, display_name, country_code) from the
    synchronous validation in the request handler; falls back to geocoding here
    for backward compatibility.
    """
    from app.database import SessionLocal

    try:
        # 1. Geocode (or use pre-computed result from request handler)
        if geocoded is not None:
            lat, lon, display_name, country_code = geocoded
        else:
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

        # 5. Generate HTML report → render to PDF via Chrome
        html = generate_html_report(
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
        pdf_bytes = html_to_pdf(html)
        if pdf_bytes is None:
            # Fallback: send HTML as attachment
            pdf_bytes = html.encode("utf-8")
            logger.warning("PDF rendering failed, sending HTML as fallback for %s", email)

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
    # If address provided: validate synchronously via geocoding BEFORE saving
    # the lead, so the user gets immediate feedback on typos instead of a silent
    # failure in the background report pipeline.
    geocoded: tuple[float, float, str, str] | None = None
    address_clean: str | None = None
    if payload.address and payload.address.strip():
        address_clean = payload.address.strip()
        # geocode_address raises HTTPException(422) if Nominatim returns no
        # results; that propagates as-is to the client with detail message
        # "Adresse konnte nicht gefunden werden".
        geocoded = await geocode_address(address_clean)

    # Merge address into quiz_answers so it's visible in admin dashboard
    answers_with_address = dict(payload.answers or {})
    if payload.address:
        answers_with_address["address"] = payload.address

    lead = Lead(
        email=payload.email,
        quiz_answers=answers_with_address,
        source=payload.source,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Schedule background report generation with the already-verified geocode
    if address_clean and geocoded:
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=payload.email,
            address=address_clean,
            answers=payload.answers or {},
            db_url="",  # uses SessionLocal directly
            geocoded=geocoded,
        )

    return LeadResponse(
        id=str(lead.id),
        email=lead.email,
        created_at=lead.created_at,
    )
