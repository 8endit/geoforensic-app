"""Lead capture endpoint — quiz/landing form -> geocode -> report -> email.

Architecture:
    source in TEASER_SOURCES -> short teaser PDF (bodenbericht.de lead magnet)
    source not in TEASER_SOURCES -> full PDF (geoforensic.de product)

Both paths share the same data pipeline (geocode, EGMS query, soil profile)
and persist a Report row. They differ only in the PDF rendering step and
the wording of the outbound mail (see ``email_service.is_teaser``).

The full-report path is wired but not yet customer-facing — there is no
checkout UI, no Stripe webhook gate, and no source on the live landing
that emits anything other than the teaser. Triggering the full report
today requires posting a non-teaser source directly to ``/api/leads``.
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db
from app.email_service import send_report_email
from app.flood_data import query_flood
from app.full_report import generate_full_report
from app.html_report import generate_html_report
from app.kostra_data import KostraLoader
from app.mining_nrw import query_mining_nrw
from app.models import Ampel, Lead, Report, ReportStatus
from app.pdf_renderer import html_to_pdf
from app.rate_limit import limiter
from app.routers.reports import geocode_address
from app.soil_data import SoilDataLoader
from app.static_map import fetch_static_map

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)

# Sources that receive the free teaser PDF (bodenbericht.de lead-magnet flow).
# Anything not listed here is treated as a paid/full-report request.
TEASER_SOURCES = {"quiz", "landing", "premium-waitlist"}


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
    geocoded: tuple[float, float, str, str, dict] | None = None,
    source: str = "quiz",
    lead_id: "uuid.UUID | None" = None,
) -> None:
    """Background task: geocode → EGMS query → PDF → email.

    Accepts pre-computed geocode (lat, lon, display_name, country_code) from the
    synchronous validation in the request handler; falls back to geocoding here
    for backward compatibility.

    The ``source`` argument selects which report variant gets rendered and
    which email template is used.  Sources in ``TEASER_SOURCES`` yield the
    short teaser PDF; any other source produces the full PDF
    (`generate_full_report`). Both share the geocode + EGMS + soil
    pipeline below.
    """
    from app.database import SessionLocal

    is_teaser = source in TEASER_SOURCES

    try:
        # 1. Geocode (or use pre-computed result from request handler)
        if geocoded is not None:
            lat, lon, display_name, country_code, region = geocoded
        else:
            lat, lon, display_name, country_code, region = await geocode_address(address)

        # 2. EGMS query — radius comes from settings so copy in the PDF
        #    and the SQL query can never drift apart.
        settings = get_settings()
        radius_m = settings.egms_radius_m
        # Threshold above which a measurement point counts as "elevated" for
        # the Ampel-begruendung line in the report. 2 mm/a is the
        # standard gelb/yellow boundary used throughout the app.
        ELEVATED_THRESHOLD_MM_YR = 2.0
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
                        :radius_m
                    )
                    ORDER BY distance_m ASC
                    """
                ),
                {"lat": lat, "lon": lon, "radius_m": radius_m},
            )
            points = [dict(row._mapping) for row in result]

            # Aggregated quarterly time series across all points in the radius.
            # Values are average cumulative displacement in mm — we hand them
            # to the report template which renders a qualitative chart (no
            # numeric y-axis labels), so the raw mm numbers stay behind the
            # paywall while the shape of the trend is visible for free.
            ts_result = await db.execute(
                text(
                    """
                    SELECT
                        DATE_TRUNC('quarter', t.measurement_date)::date AS period,
                        AVG(t.displacement_mm) AS avg_displacement
                    FROM egms_timeseries t
                    JOIN egms_points p ON t.point_id = p.id
                    WHERE ST_DWithin(
                        p.geom::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                        :radius_m
                    )
                    GROUP BY period
                    ORDER BY period
                    """
                ),
                {"lat": lat, "lon": lon, "radius_m": radius_m},
            )
            timeseries = [
                (row._mapping["period"], float(row._mapping["avg_displacement"]))
                for row in ts_result
            ]

        # 3. Compute metrics
        if points:
            velocities = [abs(float(p["mean_velocity_mm_yr"])) for p in points]
            mean_v = sum(velocities) / len(velocities)
            max_v = max(velocities)
            ampel, geo_score = _ampel_from_velocity(mean_v)
            elevated_count = sum(1 for v in velocities if v > ELEVATED_THRESHOLD_MM_YR)
        else:
            mean_v, max_v, ampel, geo_score = 0.0, 0.0, "gruen", None
            elevated_count = 0

        # 4. Query soil data (SoilGrids + LUCAS + CORINE)
        try:
            soil_loader = SoilDataLoader.get()
            soil_profile = soil_loader.query_full_profile(lat, lon)
        except Exception:
            logger.warning("Soil data query failed for (%s, %s), using empty profile", lat, lon)
            soil_profile = {}

        # 5. Generate the PDF. Teaser variant uses the HTML template +
        #    Chrome-headless renderer (with a static OSM map on page 1);
        #    the full variant uses FPDF directly and does not embed a
        #    map, so we skip the static-map fetch in that branch.
        # mining_data, kostra_data, flood_data carry the per-layer
        # lookup results (or None if not queried for this address /
        # branch). Defined here so they stay in scope for the audit log
        # in step 6 regardless of which branch ran.
        mining_data: dict | None = None
        kostra_data: dict | None = None
        flood_data: dict | None = None
        if is_teaser:
            map_data_uri = await fetch_static_map(lat, lon)
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
                radius_m=radius_m,
                map_data_uri=map_data_uri,
                region=region,
                timeseries=timeseries,
                elevated_count=elevated_count,
                elevated_threshold_mm_yr=ELEVATED_THRESHOLD_MM_YR,
            )
            pdf_bytes = html_to_pdf(html)
            if pdf_bytes is None:
                # Fallback: send HTML as attachment
                pdf_bytes = html.encode("utf-8")
                logger.warning("PDF rendering failed, sending HTML as fallback for %s", email)
        else:
            # NRW Bergbau: only query the WMS for addresses that
            # Nominatim resolved into Nordrhein-Westfalen. The PDF section
            # handles all three states (mining_data is None / error /
            # in_zone False / in_zone True).
            if (region or {}).get("state") == "Nordrhein-Westfalen":
                try:
                    mining_data = await query_mining_nrw(lat, lon)
                except Exception:
                    logger.exception(
                        "NRW Bergbau lookup failed unexpectedly for (%s, %s); "
                        "report will render the service-unavailable notice.",
                        lat, lon,
                    )
                    mining_data = {"in_zone": False, "fields": [], "error": "lookup_exception"}

            # BfG Hochwasser: nationaler Aggregat, deckt DE-Adressen ab.
            # Bei NL/AT/CH liefert das WMS einfach nichts und die Sektion
            # zeigt "nicht im Gebiet" — das ist akzeptabel als first cut;
            # eine Country-Gate-Optimierung können wir später ergänzen.
            if country_code.lower() == "de":
                try:
                    flood_data = await query_flood(lat, lon)
                except Exception:
                    logger.exception(
                        "BfG flood lookup failed unexpectedly for (%s, %s); "
                        "report will render the service-unavailable notice.",
                        lat, lon,
                    )
                    flood_data = {
                        "any_in_zone": False,
                        "scenarios": {},
                        "error": "lookup_exception",
                    }

            # KOSTRA Starkregen: für alle DE-Adressen, sofern Raster
            # verfügbar. Loader-Singleton degradiert sauber wenn die
            # Files nicht auf Platte liegen — query() liefert dann
            # available=False und der Report rendert "Daten in
            # Vorbereitung".
            if country_code.lower() == "de":
                try:
                    kostra_data = KostraLoader.get().query(lat, lon)
                except Exception:
                    logger.exception(
                        "KOSTRA lookup failed unexpectedly for (%s, %s); "
                        "report will render the unavailable-state notice.",
                        lat, lon,
                    )
                    kostra_data = {"available": False, "slots": {}}

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
                mining_data=mining_data,
                kostra_data=kostra_data,
                flood_data=flood_data,
            )

        # 6. Persist a Report row for this lead (C1). The row carries all
        #    structured values the template used — ampel, geo_score,
        #    point_count, elevated_count, mean/max velocity, region, how
        #    many timeseries quarters were available — so the admin can
        #    audit what went into the mail without re-running the pipeline.
        #
        #    The PDF bytes themselves are NOT stored here (see ticket C2).
        #    Exception safety: any DB failure is logged and swallowed so
        #    the email still goes out. Losing the email over a DB hiccup
        #    would be worse than losing the audit spur for that one lead.
        report_id: uuid.UUID | None = None
        if lead_id is not None:
            try:
                country_code_str = (country_code or "").upper()[:2] or "DE"
                report_data = {
                    "point_count": len(points),
                    "elevated_count": elevated_count,
                    "elevated_threshold_mm_yr": ELEVATED_THRESHOLD_MM_YR,
                    "mean_velocity_mm_yr": round(mean_v, 3) if points else None,
                    "max_velocity_mm_yr": round(max_v, 3) if points else None,
                    "timeseries_quarters": len(timeseries),
                    "radius_m": radius_m,
                    "region": region or {},
                    "source": source,
                    "is_teaser": is_teaser,
                    "address_display": display_name,
                    # Compact audit records of the per-layer lookups —
                    # full feature attributes stay out of the audit JSONB.
                    "mining_nrw": (
                        {
                            "in_zone": bool(mining_data.get("in_zone")),
                            "fields_count": len(mining_data.get("fields") or []),
                            "error": mining_data.get("error"),
                        }
                        if mining_data is not None
                        else None
                    ),
                    "flood_bfg": (
                        {
                            "any_in_zone": bool(flood_data.get("any_in_zone")),
                            "scenarios_in_zone": [
                                k for k, v in (flood_data.get("scenarios") or {}).items()
                                if v.get("in_zone") is True
                            ],
                            "error": flood_data.get("error"),
                        }
                        if flood_data is not None
                        else None
                    ),
                    "kostra": (
                        {
                            "available": bool(kostra_data.get("available")),
                            "slots_with_value": [
                                k for k, v in (kostra_data.get("slots") or {}).items()
                                if v.get("value") is not None
                            ],
                        }
                        if kostra_data is not None
                        else None
                    ),
                }
                async with SessionLocal() as db:
                    ampel_enum = Ampel(ampel) if ampel in {"gruen", "gelb", "rot"} else None
                    report = Report(
                        user_id=None,
                        lead_id=lead_id,
                        address_input=display_name,
                        latitude=lat,
                        longitude=lon,
                        radius_m=radius_m,
                        country=country_code_str,
                        status=ReportStatus.completed,
                        ampel=ampel_enum,
                        geo_score=geo_score,
                        paid=False,
                        report_data=report_data,
                        # Persist the exact PDF bytes that were just mailed
                        # so the admin can redownload the historic version.
                        # On HTML fallback (PDF-render failed, pdf_bytes
                        # already contains html.encode('utf-8')), we still
                        # store it — the endpoint's Content-Type check
                        # handles that case.
                        pdf_bytes=pdf_bytes,
                    )
                    db.add(report)
                    await db.commit()
                    await db.refresh(report)
                    report_id = report.id
            except Exception:
                logger.exception(
                    "Failed to persist Report row for lead_id=%s (email=%s) — "
                    "mail will still be sent, audit spur is lost for this lead.",
                    lead_id, email,
                )

        # 7. Send email
        await send_report_email(
            recipient_email=email,
            report_address=display_name,
            pdf_bytes=pdf_bytes,
            report_id=f"lead-{email}",
            is_teaser=is_teaser,
        )
        logger.info(
            "Lead report sent to %s for address %s (%s, %d pts, source=%s, teaser=%s, report_id=%s)",
            email, address, ampel, len(points), source, is_teaser, report_id,
        )

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
    geocoded: tuple[float, float, str, str, dict] | None = None
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

    # Schedule background report generation with the already-verified
    # geocode. lead.id is forwarded so the background task can link its
    # Report row back to this Lead for audit.
    if address_clean and geocoded:
        background_tasks.add_task(
            _generate_and_send_lead_report,
            email=payload.email,
            address=address_clean,
            answers=payload.answers or {},
            db_url="",  # uses SessionLocal directly
            geocoded=geocoded,
            source=payload.source,
            lead_id=lead.id,
        )

    return LeadResponse(
        id=str(lead.id),
        email=lead.email,
        created_at=lead.created_at,
    )
