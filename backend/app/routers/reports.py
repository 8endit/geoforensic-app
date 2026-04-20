import asyncio
import csv
import io
import logging
import time
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.dependencies import get_current_user, get_db
from app.models import Ampel, Report, ReportStatus, User
from app.pdf_generator import generate_report_pdf
from app.rate_limit import limiter
from app.schemas import (
    PreviewRequest,
    PreviewResponse,
    ReportCreateRequest,
    ReportCreateResponse,
    ReportDetailResponse,
    ReportListItem,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])
logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "GeoForensic/1.0 (kontakt@geoforensic.de)"
NOMINATIM_MIN_INTERVAL_SECONDS = 1.0

_nominatim_lock = asyncio.Lock()
_last_nominatim_call = 0.0


async def geocode_address(address: str) -> tuple[float, float, str, str, str | None]:
    """Resolve address via Nominatim and return
    (lat, lon, display_name, country_code, state_iso).

    `state_iso` is the ISO3166-2 state code (e.g. 'DE-BY'), taken from the
    Nominatim address detail `ISO3166-2-lvl4`. None when not provided.
    """
    global _last_nominatim_call
    query = address.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Adresse darf nicht leer sein",
        )

    async with _nominatim_lock:
        # Nominatim policy: keep client-side pacing near 1 request/s.
        delay = NOMINATIM_MIN_INTERVAL_SECONDS - (time.monotonic() - _last_nominatim_call)
        if delay > 0:
            await asyncio.sleep(delay)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": 1,
                        "countrycodes": "de,nl,at,ch",
                        "addressdetails": 1,
                    },
                    headers={"User-Agent": NOMINATIM_USER_AGENT},
                    timeout=10.0,
                )
                resp.raise_for_status()
                results = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Nominatim HTTP error for %r: %s", query, exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Geocoding-Service derzeit nicht verfuegbar",
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Nominatim request failed for %r: %s", query, exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Geocoding-Service derzeit nicht erreichbar",
            ) from exc
        finally:
            _last_nominatim_call = time.monotonic()

    if not results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Adresse konnte nicht gefunden werden",
        )

    hit = results[0]
    addr = hit.get("address", {})
    country_code = addr.get("country_code", "").lower()
    state_iso = addr.get("ISO3166-2-lvl4") or None
    return float(hit["lat"]), float(hit["lon"]), str(hit["display_name"]), country_code, state_iso


async def query_egms_points(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_m: int = 500,
) -> list[dict]:
    """Fetch EGMS points around a coordinate within radius in meters."""
    result = await db.execute(
        text(
            """
            SELECT
                ST_Y(geom) AS lat,
                ST_X(geom) AS lon,
                mean_velocity_mm_yr,
                velocity_std,
                coherence,
                ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distance_m
            FROM egms_points
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY distance_m ASC
            """
        ),
        {"lat": lat, "lon": lon, "radius": radius_m},
    )
    return [dict(row._mapping) for row in result]


def _ampel_from_velocity(abs_velocity: float) -> tuple[Ampel, int]:
    if abs_velocity < 2:
        return Ampel.gruen, 90
    if abs_velocity <= 5:
        return Ampel.gelb, 70
    return Ampel.rot, 45


def _build_histogram(velocities: list[float]) -> dict[str, int]:
    bins = {"0-2": 0, "2-5": 0, "5-8": 0, "8-12": 0, "12+": 0}
    for velocity in velocities:
        if velocity < 2:
            bins["0-2"] += 1
        elif velocity < 5:
            bins["2-5"] += 1
        elif velocity < 8:
            bins["5-8"] += 1
        elif velocity < 12:
            bins["8-12"] += 1
        else:
            bins["12+"] += 1
    return bins


async def _run_report_pipeline(report_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            return

        try:
            # Preserve modules selected at creation time (before pipeline overwrites report_data)
            selected_modules = (report.report_data or {}).get("selected_modules", ["classic"])

            points = await query_egms_points(db, report.latitude, report.longitude, report.radius_m)
            if not points:
                report.status = ReportStatus.completed
                report.ampel = None
                report.geo_score = None
                report.report_data = {
                    "selected_modules": selected_modules,
                    "analysis": {
                        "summary": "Keine EGMS-Messpunkte im Untersuchungsradius gefunden.",
                        "point_count": 0,
                        "max_abs_velocity_mm_yr": 0.0,
                        "mean_velocity_mm_yr": 0.0,
                        "median_velocity_mm_yr": 0.0,
                        "weighted_velocity_mm_yr": 0.0,
                        "data_source": "EGMS Ortho L3 (Copernicus)",
                        "attribution": "Generated using European Union's Copernicus Land Monitoring Service information",
                    },
                    "velocity_histogram": _build_histogram([]),
                    "geo_score": None,
                    "raw_points": [],
                }
                await db.commit()
                return

            velocities = [abs(float(point["mean_velocity_mm_yr"])) for point in points]
            max_velocity = max(velocities)
            mean_velocity = sum(velocities) / len(velocities)
            ordered_velocities = sorted(velocities)
            mid = len(ordered_velocities) // 2
            if len(ordered_velocities) % 2 == 0:
                median_velocity = (ordered_velocities[mid - 1] + ordered_velocities[mid]) / 2
            else:
                median_velocity = ordered_velocities[mid]

            weighted_sum = 0.0
            weight_total = 0.0
            for point in points:
                distance = float(point["distance_m"])
                weight = max(0.1, 1.0 - (distance / report.radius_m))
                weighted_sum += abs(float(point["mean_velocity_mm_yr"])) * weight
                weight_total += weight
            weighted_velocity = weighted_sum / weight_total if weight_total else mean_velocity

            ampel, geo_score = _ampel_from_velocity(weighted_velocity)

            report.ampel = ampel
            report.geo_score = geo_score
            report.status = ReportStatus.completed
            report.report_data = {
                "selected_modules": selected_modules,
                "analysis": {
                    "summary": (
                        f"Analyse basierend auf {len(points)} EGMS-Messpunkten "
                        f"im Radius von {report.radius_m}m."
                    ),
                    "point_count": len(points),
                    "max_abs_velocity_mm_yr": round(max_velocity, 2),
                    "mean_velocity_mm_yr": round(mean_velocity, 2),
                    "median_velocity_mm_yr": round(median_velocity, 2),
                    "weighted_velocity_mm_yr": round(weighted_velocity, 2),
                    "data_source": "EGMS Ortho L3 (Copernicus)",
                    "attribution": "Generated using European Union's Copernicus Land Monitoring Service information",
                },
                "velocity_histogram": _build_histogram(velocities),
                "geo_score": geo_score,
                "raw_points": [
                    {
                        "lat": round(float(point["lat"]), 6),
                        "lon": round(float(point["lon"]), 6),
                        "velocity_mm_yr": round(float(point["mean_velocity_mm_yr"]), 2),
                        "distance_m": round(float(point["distance_m"]), 1),
                        "coherence": round(float(point.get("coherence") or 0.0), 2),
                    }
                    for point in points[:200]
                ],
            }
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Report pipeline failed for %s", report_id)
            report.status = ReportStatus.failed
            report.report_data = {"error": str(exc), "selected_modules": selected_modules}
            await db.commit()


@router.post("/preview", response_model=PreviewResponse)
@limiter.limit("100/hour")
async def preview_report(
    request: Request,
    payload: PreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    lat, lon, display_name, country_code, _state_iso = await geocode_address(payload.address)
    try:
        points = await query_egms_points(db, lat, lon, radius_m=500)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Preview query failed for %r", payload.address)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EGMS-Datenbank derzeit nicht verfuegbar",
        ) from exc
    if points:
        max_velocity = max(abs(float(point["mean_velocity_mm_yr"])) for point in points)
        ampel, _ = _ampel_from_velocity(max_velocity)
    else:
        ampel = None

    return PreviewResponse(
        ampel=ampel.value if ampel else "gruen",
        point_count=len(points),
        address_resolved=display_name,
        latitude=lat,
        longitude=lon,
    )


@router.post("/create", response_model=ReportCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportCreateResponse:
    lat, lon, display_name, country_code, _state_iso = await geocode_address(payload.address)
    selected_modules = list(dict.fromkeys(payload.selected_modules))
    report = Report(
        user_id=current_user.id,
        address_input=display_name,
        latitude=lat,
        longitude=lon,
        radius_m=payload.radius_m,
        aktenzeichen=payload.aktenzeichen,
        status=ReportStatus.processing,
        paid=False,
        country=country_code.upper() or "DE",
        report_data={"selected_modules": selected_modules},
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    background_tasks.add_task(_run_report_pipeline, report.id)
    return ReportCreateResponse.model_validate(report)


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportListItem]:
    result = await db.execute(
        select(Report).where(Report.user_id == current_user.id).order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return [ReportListItem.model_validate(r) for r in reports]


async def _get_report_for_user(report_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id, Report.user_id == user_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    report = await _get_report_for_user(report_id, current_user.id, db)
    payload = ReportDetailResponse.model_validate(report)
    payload.pdf_available = bool(report.paid and report.status == ReportStatus.completed)
    return payload


@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = await _get_report_for_user(report_id, current_user.id, db)
    if not report.paid:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Report is not paid")

    try:
        pdf_bytes = generate_report_pdf(report)
    except RuntimeError as exc:
        logger.exception("PDF generation failed for report %s", report_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF-Service derzeit nicht verfuegbar",
        ) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="geoforensic-{report.id}.pdf"'},
    )


@router.get("/{report_id}/raw.csv")
async def get_report_csv(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    report = await _get_report_for_user(report_id, current_user.id, db)
    if not report.paid:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Report is not paid")

    rows = (report.report_data or {}).get("raw_points", [])
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["lat", "lon", "velocity_mm_yr", "distance_m", "coherence"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    data = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return StreamingResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.csv"'},
    )

