import csv
import hashlib
import io
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.dependencies import get_current_user, get_db
from app.models import Ampel, Report, ReportStatus, User
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


def _mock_geocode(address: str) -> tuple[float, float]:
    digest = hashlib.sha256(address.lower().encode("utf-8")).hexdigest()
    lat_seed = int(digest[:8], 16) / 0xFFFFFFFF
    lon_seed = int(digest[8:16], 16) / 0xFFFFFFFF
    lat = 47.2 + (55.1 - 47.2) * lat_seed
    lon = 5.8 + (15.1 - 5.8) * lon_seed
    return round(lat, 6), round(lon, 6)


def _ampel_from_velocity(abs_velocity: float) -> tuple[Ampel, int]:
    if abs_velocity < 2:
        return Ampel.gruen, 90
    if abs_velocity <= 5:
        return Ampel.gelb, 70
    return Ampel.rot, 45


async def _run_mock_report_pipeline(report_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            return

        # Deterministic "analysis" from report location for repeatable MVP output.
        seed = abs(hash((round(report.latitude, 3), round(report.longitude, 3), report.radius_m)))
        abs_velocity = round((seed % 75) / 10.0, 1)
        ampel, score = _ampel_from_velocity(abs_velocity)
        point_count = max(8, min(150, int((seed % 140) + 8)))

        report.ampel = ampel
        report.geo_score = score
        report.status = ReportStatus.completed
        report.report_data = {
            "analysis": {
                "summary": f"Mock analysis generated at {datetime.now(UTC).isoformat()}",
                "point_count": point_count,
                "max_abs_velocity_mm_yr": abs_velocity,
            },
            "geology": {"risk_level": "moderate" if ampel != Ampel.gruen else "low"},
            "flood": {"zone": "B", "score": 0.34},
            "slope": {"mean_degree": round((seed % 120) / 10.0, 1)},
            "geo_score": score,
            "raw_points": [
                {
                    "lat": round(report.latitude + ((i % 5) * 0.0003), 6),
                    "lon": round(report.longitude + ((i % 7) * 0.0003), 6),
                    "velocity_mm_yr": round(((i % 11) - 5) * 0.7, 2),
                }
                for i in range(min(point_count, 80))
            ],
        }
        await db.commit()


@router.post("/preview", response_model=PreviewResponse)
@limiter.limit("10/hour")
async def preview_report(request: Request, payload: PreviewRequest) -> PreviewResponse:
    lat, lon = _mock_geocode(payload.address)
    seed = abs(hash(payload.address.lower()))
    abs_velocity = round((seed % 70) / 10.0, 1)
    ampel, _ = _ampel_from_velocity(abs_velocity)
    point_count = int((seed % 35) + 3)
    return PreviewResponse(
        ampel=ampel.value,
        point_count=point_count,
        address_resolved=payload.address.strip(),
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
    lat, lon = _mock_geocode(payload.address)
    report = Report(
        user_id=current_user.id,
        address_input=payload.address.strip(),
        latitude=lat,
        longitude=lon,
        radius_m=payload.radius_m,
        aktenzeichen=payload.aktenzeichen,
        status=ReportStatus.processing,
        paid=False,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    background_tasks.add_task(_run_mock_report_pipeline, report.id)
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
    content = (
        f"GeoForensic Report\n\nID: {report.id}\nAddress: {report.address_input}\n"
        f"Status: {report.status.value}\nAmpel: {report.ampel.value if report.ampel else 'n/a'}\n"
    ).encode("utf-8")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'},
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
    writer = csv.DictWriter(buffer, fieldnames=["lat", "lon", "velocity_mm_yr"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    data = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return StreamingResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.csv"'},
    )

