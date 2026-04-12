"""Import EGMS CSV files into PostGIS table egms_points.

Usage:
    python -m scripts.import_egms_csv --csv /path/to/egms_de.csv --country DE
"""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import text

from app.database import SessionLocal

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
    VALUES (
        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
        :vel,
        :std,
        :coh,
        :measurement_start,
        :measurement_end,
        :country
    )
    """
)


def _to_float(value: str | None, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    return float(value)


def _detect(row: dict[str, str], *candidates: str) -> str | None:
    lowered = {key.lower(): key for key in row}
    for candidate in candidates:
        if candidate in row:
            return candidate
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


async def import_egms_csv(csv_path: Path, country: str = "DE", batch_size: int = 10000) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    inserted = 0
    async with SessionLocal() as db:
        with csv_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise RuntimeError("CSV has no header row")

            first_row = next(reader, None)
            if first_row is None:
                print("CSV empty, nothing imported.")
                return

            lat_key = _detect(first_row, "latitude", "lat")
            lon_key = _detect(first_row, "longitude", "lon", "lng")
            vel_key = _detect(first_row, "mean_velocity_mm_yr", "mean_velocity", "velocity")
            std_key = _detect(first_row, "velocity_std", "std")
            coh_key = _detect(first_row, "coherence")
            start_key = _detect(first_row, "measurement_period_start", "measurement_start")
            end_key = _detect(first_row, "measurement_period_end", "measurement_end")

            if not lat_key or not lon_key or not vel_key:
                raise RuntimeError("CSV header missing required columns for lat/lon/velocity")

            def map_row(row: dict[str, str]) -> dict:
                return {
                    "lat": float(row[lat_key]),
                    "lon": float(row[lon_key]),
                    "vel": float(row[vel_key]),
                    "std": _to_float(row.get(std_key)) if std_key else None,
                    "coh": _to_float(row.get(coh_key)) if coh_key else None,
                    "measurement_start": row.get(start_key) if start_key else None,
                    "measurement_end": row.get(end_key) if end_key else None,
                    "country": country,
                }

            batch: list[dict] = [map_row(first_row)]
            for row in reader:
                batch.append(map_row(row))
                if len(batch) >= batch_size:
                    await db.execute(INSERT_SQL, batch)
                    await db.commit()
                    inserted += len(batch)
                    print(f"Imported {inserted} rows...")
                    batch = []

            if batch:
                await db.execute(INSERT_SQL, batch)
                await db.commit()
                inserted += len(batch)

    print(f"Import complete: {inserted} rows from {csv_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import EGMS CSV into PostGIS.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to EGMS CSV file")
    parser.add_argument("--country", default="DE", type=str, help="Country code, e.g. DE/NL")
    parser.add_argument("--batch-size", default=10000, type=int, help="Rows per bulk insert")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(import_egms_csv(args.csv, country=args.country.upper(), batch_size=args.batch_size))
