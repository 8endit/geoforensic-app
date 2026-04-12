"""Import EGMS data into PostGIS.

Usage:
    python -m scripts.import_egms path/to/egms_data.csv --country DE
    python -m scripts.import_egms path/to/egms_data.gpkg --country NL
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

CSV_TYPES = {".csv", ".txt"}
GPKG_TYPES = {".gpkg"}


@dataclass
class EgmsRow:
    lat: float
    lon: float
    mean_velocity_mm_yr: float
    velocity_std: float | None
    coherence: float | None
    measurement_start: dt.date | None
    measurement_end: dt.date | None
    country: str


INSERT_SQL = text(
    """
    INSERT INTO egms_points (
        geom,
        mean_velocity_mm_yr,
        velocity_std,
        coherence,
        measurement_start,
        measurement_end,
        country
    )
    SELECT
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
        :vel,
        :std,
        :coh,
        :measurement_start,
        :measurement_end,
        :country
    WHERE NOT EXISTS (
        SELECT 1
        FROM egms_points ep
        WHERE ep.country = :country
          AND abs(ST_X(ep.geom) - :lon) < 0.0000001
          AND abs(ST_Y(ep.geom) - :lat) < 0.0000001
          AND abs(ep.mean_velocity_mm_yr - :vel) < 0.0001
          AND COALESCE(ep.measurement_start::text, '') = COALESCE(:measurement_start::text, '')
          AND COALESCE(ep.measurement_end::text, '') = COALESCE(:measurement_end::text, '')
    )
    """
)


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    txt = str(value).strip()
    if txt == "" or txt.lower() == "nan":
        return None
    return float(txt)


def _parse_date(value: object) -> dt.date | None:
    if value is None:
        return None
    txt = str(value).strip()
    if txt == "" or txt.lower() == "nan":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return dt.datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def _pick_key(columns: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def _dedupe_rows(rows: list[EgmsRow]) -> list[EgmsRow]:
    seen: set[tuple] = set()
    out: list[EgmsRow] = []
    for row in rows:
        key = (
            round(row.lat, 7),
            round(row.lon, 7),
            round(row.mean_velocity_mm_yr, 4),
            round(row.velocity_std or 0.0, 4),
            round(row.coherence or 0.0, 4),
            row.measurement_start.isoformat() if row.measurement_start else "",
            row.measurement_end.isoformat() if row.measurement_end else "",
            row.country,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _row_to_params(row: EgmsRow) -> dict:
    return {
        "lat": row.lat,
        "lon": row.lon,
        "vel": row.mean_velocity_mm_yr,
        "std": row.velocity_std,
        "coh": row.coherence,
        "measurement_start": row.measurement_start,
        "measurement_end": row.measurement_end,
        "country": row.country,
    }


def _iter_csv_rows(path: Path, country: str) -> Iterable[EgmsRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError("CSV has no header row")

        cols = list(reader.fieldnames)
        lat_key = _pick_key(cols, ["latitude", "lat", "y_lat", "y"])
        lon_key = _pick_key(cols, ["longitude", "lon", "lng", "x_lon", "x"])
        vel_key = _pick_key(
            cols,
            ["mean_velocity_mm_yr", "mean_velocity", "velocity", "mean_vel", "vel"],
        )
        std_key = _pick_key(cols, ["velocity_std", "std", "stdev"])
        coh_key = _pick_key(cols, ["coherence", "coh"])
        start_key = _pick_key(cols, ["measurement_start", "measurement_period_start", "start_date"])
        end_key = _pick_key(cols, ["measurement_end", "measurement_period_end", "end_date"])

        if not lat_key or not lon_key or not vel_key:
            raise RuntimeError("CSV must contain latitude/longitude/mean_velocity columns")

        for raw in reader:
            lat = _to_float(raw.get(lat_key))
            lon = _to_float(raw.get(lon_key))
            vel = _to_float(raw.get(vel_key))
            if lat is None or lon is None or vel is None:
                continue
            yield EgmsRow(
                lat=lat,
                lon=lon,
                mean_velocity_mm_yr=vel,
                velocity_std=_to_float(raw.get(std_key)) if std_key else None,
                coherence=_to_float(raw.get(coh_key)) if coh_key else None,
                measurement_start=_parse_date(raw.get(start_key)) if start_key else None,
                measurement_end=_parse_date(raw.get(end_key)) if end_key else None,
                country=country,
            )


def _iter_gpkg_rows(path: Path, country: str) -> Iterable[EgmsRow]:
    try:
        import geopandas as gpd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "GeoPackage import requires geopandas. "
            "Install backend/scripts/requirements-import.txt first."
        ) from exc

    gdf = gpd.read_file(path)
    if gdf.empty:
        return

    if gdf.crs is None:
        raise RuntimeError("GeoPackage has no CRS information")
    if str(gdf.crs).lower() not in {"epsg:4326", "4326"}:
        gdf = gdf.to_crs(epsg=4326)

    cols = [c for c in gdf.columns if c != "geometry"]
    vel_key = _pick_key(cols, ["mean_velocity_mm_yr", "mean_velocity", "velocity", "mean_vel", "vel"])
    std_key = _pick_key(cols, ["velocity_std", "std", "stdev"])
    coh_key = _pick_key(cols, ["coherence", "coh"])
    start_key = _pick_key(cols, ["measurement_start", "measurement_period_start", "start_date"])
    end_key = _pick_key(cols, ["measurement_end", "measurement_period_end", "end_date"])
    if not vel_key:
        raise RuntimeError("GeoPackage must contain mean_velocity column")

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if geom.geom_type != "Point":
            continue

        vel = _to_float(row.get(vel_key))
        if vel is None:
            continue
        yield EgmsRow(
            lat=float(geom.y),
            lon=float(geom.x),
            mean_velocity_mm_yr=vel,
            velocity_std=_to_float(row.get(std_key)) if std_key else None,
            coherence=_to_float(row.get(coh_key)) if coh_key else None,
            measurement_start=_parse_date(row.get(start_key)) if start_key else None,
            measurement_end=_parse_date(row.get(end_key)) if end_key else None,
            country=country,
        )


async def _insert_batches(
    rows: Iterable[EgmsRow],
    session_factory: async_sessionmaker[AsyncSession],
    batch_size: int,
) -> tuple[int, int]:
    read_count = 0
    inserted_count = 0
    batch: list[EgmsRow] = []

    async with session_factory() as db:
        for row in rows:
            batch.append(row)
            read_count += 1
            if len(batch) >= batch_size:
                deduped = _dedupe_rows(batch)
                params = [_row_to_params(r) for r in deduped]
                if params:
                    result = await db.execute(INSERT_SQL, params)
                    inserted_count += result.rowcount or 0
                    await db.commit()
                if read_count % 50000 == 0:
                    print(f"Progress: read {read_count:,} rows, inserted {inserted_count:,} rows")
                batch = []

        if batch:
            deduped = _dedupe_rows(batch)
            params = [_row_to_params(r) for r in deduped]
            if params:
                result = await db.execute(INSERT_SQL, params)
                inserted_count += result.rowcount or 0
                await db.commit()

    return read_count, inserted_count


async def import_egms(path: Path, country: str = "DE", batch_size: int = 10000) -> None:
    if not path.exists():
        raise FileNotFoundError(path)

    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    suffix = path.suffix.lower()
    if suffix in CSV_TYPES:
        rows = _iter_csv_rows(path, country=country)
    elif suffix in GPKG_TYPES:
        rows = _iter_gpkg_rows(path, country=country)
    else:
        raise RuntimeError(f"Unsupported file type: {suffix}. Use CSV or GPKG.")

    read_count, inserted_count = await _insert_batches(rows, session_factory, batch_size=batch_size)
    await engine.dispose()

    print("Import finished.")
    print(f"Rows read: {read_count:,}")
    print(f"Rows inserted (new): {inserted_count:,}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import EGMS CSV/GPKG into PostGIS.")
    parser.add_argument("path", type=Path, help="Path to EGMS CSV or GPKG")
    parser.add_argument("--country", default="DE", type=str, help="Country code (e.g. DE, NL)")
    parser.add_argument("--batch-size", default=10000, type=int, help="Rows per batch insert")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(import_egms(args.path, country=args.country.upper(), batch_size=args.batch_size))
