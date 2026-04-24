"""Regenerate the teaser PDF for an existing lead — for admin inspection.

Runs inside the backend container. Pulls the Lead row by email, walks the
same pipeline as the original lead flow (geocode, EGMS query, soil profile,
static map, html render, PDF), and writes the resulting PDF into /tmp/
**without** sending an email.

Usage inside the container:
    python -m backend.scripts.regenerate_report <email>

From the host, use the wrapper scripts/regenerate-report.sh which runs this
inside the backend container and copies the PDF out.

IMPORTANT: this reproduces the report as it would look **today**, with the
current code and current backing data. It is NOT a historical replay of
what was actually sent to the recipient when the lead came in. The script
prints the original lead timestamp vs. the regeneration timestamp so the
reader can gauge how far the code + data have moved on since then.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text

from app.config import get_settings
from app.database import SessionLocal
from app.html_report import generate_html_report
from app.models import Lead
from app.pdf_renderer import html_to_pdf
from app.routers.leads import _ampel_from_velocity
from app.routers.reports import geocode_address
from app.soil_data import SoilDataLoader
from app.static_map import fetch_static_map


OUT_DIR = Path("/tmp/regenerated-reports")


def _fmt_ts(ts: datetime | None) -> str:
    if ts is None:
        return "-"
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def regenerate(email: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()

    async with SessionLocal() as db:
        result = await db.execute(
            select(Lead).where(Lead.email == email).order_by(Lead.created_at.desc())
        )
        leads = result.scalars().all()

    if not leads:
        print(f"No lead found for {email!r}")
        return 1

    now = datetime.now(timezone.utc)
    print(f"Regenerating {len(leads)} lead(s) for {email}")
    print(f"Current time (UTC): {_fmt_ts(now)}")
    print()

    for i, lead in enumerate(leads, 1):
        answers = lead.quiz_answers or {}
        address = answers.get("address") or ""
        delta_days = (now - lead.created_at).days if lead.created_at else -1

        print(f"[{i}/{len(leads)}] Lead {lead.id}")
        print(f"    source:        {lead.source}")
        print(f"    created_at:    {_fmt_ts(lead.created_at)}")
        print(f"    delta (days):  {delta_days}")
        print(f"    address:       {address or '(missing)'}")

        if not address:
            print(f"    SKIP — no address in quiz_answers")
            print()
            continue

        try:
            lat, lon, normalized_addr, _cc, region = await geocode_address(address)
            print(f"    normalized:    {normalized_addr}")
            print(f"    coords:        {lat:.4f}, {lon:.4f}")
            if region:
                region_line = " · ".join(
                    v for v in (region.get("county"), region.get("state"), region.get("country")) if v
                )
                if region_line:
                    print(f"    region:        {region_line}")

            radius_m = settings.egms_radius_m
            ELEVATED_THRESHOLD_MM_YR = 2.0
            async with SessionLocal() as db:
                res = await db.execute(
                    text(
                        """
                        SELECT mean_velocity_mm_yr
                        FROM egms_points
                        WHERE ST_DWithin(
                            geom::geography,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                            :radius_m
                        )
                        """
                    ),
                    {"lat": lat, "lon": lon, "radius_m": radius_m},
                )
                points = [dict(row._mapping) for row in res]

                ts_res = await db.execute(
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
                    for row in ts_res
                ]

            if points:
                velocities = [abs(float(p["mean_velocity_mm_yr"])) for p in points]
                mean_v = sum(velocities) / len(velocities)
                max_v = max(velocities)
                ampel, geo_score = _ampel_from_velocity(mean_v)
                elevated_count = sum(1 for v in velocities if v > ELEVATED_THRESHOLD_MM_YR)
            else:
                mean_v, max_v, ampel, geo_score = 0.0, 0.0, "gruen", None
                elevated_count = 0

            try:
                soil_profile = SoilDataLoader.get().query_full_profile(lat, lon)
                soil_ok = True
            except Exception as soil_exc:
                print(f"    soil data failed: {soil_exc!r}")
                soil_profile = {}
                soil_ok = False

            map_data_uri = await fetch_static_map(lat, lon)
            map_ok = bool(map_data_uri)

            html = generate_html_report(
                address=normalized_addr,
                lat=lat,
                lon=lon,
                ampel=ampel,
                point_count=len(points),
                mean_velocity=mean_v,
                max_velocity=max_v,
                geo_score=geo_score,
                soil_profile=soil_profile,
                answers=answers,
                radius_m=radius_m,
                map_data_uri=map_data_uri,
                region=region,
                timeseries=timeseries,
                elevated_count=elevated_count,
                elevated_threshold_mm_yr=ELEVATED_THRESHOLD_MM_YR,
            )
            pdf_bytes = html_to_pdf(html) or html.encode("utf-8")

            out_path = OUT_DIR / f"lead_{lead.id}_{lead.created_at.strftime('%Y%m%d')}.pdf"
            out_path.write_bytes(pdf_bytes)

            print(f"    ampel:         {ampel}")
            print(f"    geo_score:     {geo_score}")
            print(f"    points/radius: {len(points)} in {radius_m} m")
            print(f"    elevated:      {elevated_count} of {len(points)} > {ELEVATED_THRESHOLD_MM_YR} mm/a")
            print(f"    time series:   {len(timeseries)} quarterly aggregates")
            print(f"    soil data:     {'ok' if soil_ok else 'FAILED'}")
            print(f"    static map:    {'ok' if map_ok else 'FAILED (grey fallback used)'}")
            print(f"    PDF bytes:     {len(pdf_bytes)}")
            print(f"    written to:    {out_path}")
        except Exception as exc:
            print(f"    FAILED to regenerate: {exc!r}")
        print()

    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m backend.scripts.regenerate_report <email>")
        sys.exit(2)
    sys.exit(asyncio.run(regenerate(sys.argv[1])))


if __name__ == "__main__":
    main()
