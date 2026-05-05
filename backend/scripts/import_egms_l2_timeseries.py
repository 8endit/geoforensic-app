"""Import EGMS L2b Calibrated time-series CSV into egms_timeseries.

EGMS L2b ist im Wide-Format: eine Zeile pro PSI-Punkt, eine Spalte pro
Mess-Datum (YYYYMMDD), Wert = kumulative Verschiebung in mm seit erstem
Bild. Beispiel-Header (gekuerzt):

    pid;easting;northing;height;mean_velocity;mean_velocity_std;...;
    20180106;20180112;20180118;...;20221230

Wir konvertieren das beim Import in das Long-Format der
egms_timeseries-Tabelle:
    (point_id, measurement_date, displacement_mm)

Match-Strategie EGMS-pid → egms_points.id:
1. Wenn egms_points.egms_pid bereits gesetzt (neu seit Migration
   20260505_02): direkter Lookup.
2. Sonst: PostGIS-Spatial-Lookup auf <2 m Toleranz. Egms_pid wird
   dabei "im Vorbeigehen" mitgeschrieben damit nachfolgende Tiles vom
   schnellen Pfad profitieren.

Aufruf (lokal, schreibt in VPS-DB):
    DATABASE_URL=postgresql://postgres:postgres@VPS:5432/geoforensic \\
    python -m scripts.import_egms_l2_timeseries \\
        --csv F:/geoforensic-data/egms/DE-l2/EGMS_L2b_E48N32_2018_2022_1_VERT.csv

Aufruf (im Container auf VPS, Datei vorher per scp hochgeladen):
    docker compose exec backend python -m scripts.import_egms_l2_timeseries \\
        --csv /app/imports/EGMS_L2b_E48N32_2018_2022_1_VERT.csv

Performance-Erwartung:
    Berlin-Tile ~600k Punkte × ~250 Mess-Daten = ~150M Rows.
    Mit COPY und 50k-Batches geschaetzt 15-30 min pro Tile.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import os
import re
import sys
import time
from typing import Iterable

import psycopg2

DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/geoforensic"

# Datums-Header in EGMS-CSV: "20180106" oder "20180106D" o.ae.
_DATE_HEADER = re.compile(r"^(\d{8})[A-Z]?$")

# CSV-Separator: EGMS nutzt ';' in den DE-Files, manche Releases ','.
# Wir detektieren beim Open. Encoding: UTF-8 (BOM vorkommend → utf-8-sig).


def _detect_dialect(path: str) -> tuple[str, str]:
    """Return (delimiter, encoding). Schaut die ersten 4 KB an."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                head = f.read(4096)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError(f"Cannot decode {path} with utf-8/latin-1")
    if head.count(";") > head.count(","):
        return ";", enc
    return ",", enc


def _parse_csv_header(reader: csv.reader) -> tuple[list[str], list[tuple[int, dt.date]]]:
    """Return (full_header, [(col_index, date), ...] für Datums-Spalten)."""
    header = next(reader)
    date_cols: list[tuple[int, dt.date]] = []
    for i, h in enumerate(header):
        m = _DATE_HEADER.match(h.strip())
        if m:
            ymd = m.group(1)
            try:
                date_cols.append((i, dt.date(int(ymd[0:4]), int(ymd[4:6]), int(ymd[6:8]))))
            except ValueError:
                pass
    return header, date_cols


def _column_index(header: list[str], *candidates: str) -> int | None:
    """Return Index der ersten Spalte deren Name in `candidates` matched (case-insensitive)."""
    norm = [h.strip().lower() for h in header]
    for c in candidates:
        cl = c.lower()
        if cl in norm:
            return norm.index(cl)
    return None


def _resolve_point_ids(
    conn,
    pid_lat_lon: list[tuple[str, float, float]],
) -> dict[str, int]:
    """Map EGMS-pid → egms_points.id.

    Schritt 1: Direkt-Match auf egms_pid (wenn schon gesetzt).
    Schritt 2: Spatial-Lookup (<2m) für die uebrigen pids und egms_pid
    nachtraeglich speichern damit die folgenden Tiles davon profitieren.
    """
    pid_to_id: dict[str, int] = {}

    cur = conn.cursor()

    # Phase 1 — egms_pid-Match
    cur.execute(
        "CREATE TEMP TABLE _wanted_pids (pid TEXT PRIMARY KEY) ON COMMIT DROP"
    )
    cur.executemany(
        "INSERT INTO _wanted_pids (pid) VALUES (%s) ON CONFLICT DO NOTHING",
        [(p[0],) for p in pid_lat_lon],
    )
    cur.execute(
        "SELECT p.egms_pid, p.id FROM egms_points p "
        "JOIN _wanted_pids w ON w.pid = p.egms_pid"
    )
    for pid, pid_id in cur.fetchall():
        pid_to_id[pid] = pid_id

    missing = [(p, lat, lon) for (p, lat, lon) in pid_lat_lon if p not in pid_to_id]
    if not missing:
        return pid_to_id

    # Phase 2 — Spatial-Lookup für die nicht-gemappten pids
    print(f"  Spatial-resolving {len(missing):,} pids (egms_pid not yet set)...")
    cur.execute(
        "CREATE TEMP TABLE _wanted_geom ("
        "  pid TEXT PRIMARY KEY, geom geometry(Point, 4326)"
        ") ON COMMIT DROP"
    )
    cur.executemany(
        "INSERT INTO _wanted_geom (pid, geom) VALUES "
        "(%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) ON CONFLICT DO NOTHING",
        [(pid, lon, lat) for (pid, lat, lon) in missing],
    )
    cur.execute("CREATE INDEX ON _wanted_geom USING GIST (geom)")

    # Nearest-Neighbor mit Toleranz 2m. KNN-Operator <-> ist effizient.
    # Wir nutzen LATERAL um pro wanted-pid nur den nächsten egms_point zu
    # holen. ST_DWithin als hard cutoff damit wir nicht versehentlich
    # einen 50m-entfernten Punkt nehmen wenn die Datei vergiftet ist.
    cur.execute(
        """
        UPDATE egms_points p
        SET egms_pid = w.pid
        FROM _wanted_geom w
        WHERE p.id = (
            SELECT p2.id FROM egms_points p2
            WHERE ST_DWithin(p2.geom::geography, w.geom::geography, 2.0)
              AND p2.egms_pid IS NULL
            ORDER BY p2.geom <-> w.geom
            LIMIT 1
        )
        """
    )
    spatial_matched = cur.rowcount
    cur.execute(
        "SELECT p.egms_pid, p.id FROM egms_points p "
        "JOIN _wanted_geom w ON w.pid = p.egms_pid"
    )
    for pid, pid_id in cur.fetchall():
        pid_to_id[pid] = pid_id

    conn.commit()
    print(f"  Spatial-matched {spatial_matched:,} pids (now egms_pid is set, "
          f"future tiles use the fast path)")
    return pid_to_id


def _copy_timeseries_batch(
    conn,
    rows: Iterable[tuple[int, dt.date, float]],
) -> int:
    """Bulk-insert in egms_timeseries via COPY. Return Anzahl Rows."""
    cur = conn.cursor()
    buf = io.StringIO()
    n = 0
    for pid_id, d, disp in rows:
        buf.write(f"{pid_id}\t{d.isoformat()}\t{disp}\n")
        n += 1
    if n == 0:
        return 0
    buf.seek(0)
    # ON CONFLICT auf (point_id, measurement_date) ist bei COPY
    # nicht direkt — wir nutzen eine staging-Tabelle + INSERT ON CONFLICT.
    cur.execute(
        "CREATE TEMP TABLE IF NOT EXISTS _ts_stage ("
        "  point_id INTEGER, measurement_date DATE, displacement_mm DOUBLE PRECISION"
        ") ON COMMIT DROP"
    )
    cur.execute("TRUNCATE _ts_stage")
    cur.copy_expert(
        "COPY _ts_stage (point_id, measurement_date, displacement_mm) FROM STDIN",
        buf,
    )
    cur.execute(
        "INSERT INTO egms_timeseries (point_id, measurement_date, displacement_mm) "
        "SELECT point_id, measurement_date, displacement_mm FROM _ts_stage "
        "ON CONFLICT (point_id, measurement_date) DO NOTHING"
    )
    return n


def import_csv(conn, csv_path: str, batch_rows: int = 100_000) -> dict:
    """Run the full import for a single L2b CSV file."""
    delim, enc = _detect_dialect(csv_path)
    print(f"  CSV-Dialekt: delimiter={delim!r}, encoding={enc}")

    # Pass 1 — pids einsammeln + Schema parsen
    with open(csv_path, "r", encoding=enc) as f:
        reader = csv.reader(f, delimiter=delim)
        header, date_cols = _parse_csv_header(reader)
        pid_idx = _column_index(header, "pid", "p_id", "id")
        lat_idx = _column_index(header, "latitude", "lat")
        lon_idx = _column_index(header, "longitude", "lon")
        if pid_idx is None or lat_idx is None or lon_idx is None:
            raise RuntimeError(
                f"Header missing required column. Got: {header[:8]}... "
                f"Need pid + latitude + longitude columns."
            )
        if not date_cols:
            raise RuntimeError(
                "No date columns (YYYYMMDD pattern) found in header. "
                "Maybe this is the L3 Velocity-only CSV — use import_egms_csv.py instead."
            )
        print(f"  Found {len(date_cols)} measurement dates "
              f"({date_cols[0][1]}..{date_cols[-1][1]})")

        pid_lat_lon: list[tuple[str, float, float]] = []
        for row in reader:
            if not row or len(row) <= max(pid_idx, lat_idx, lon_idx):
                continue
            try:
                pid_lat_lon.append((
                    row[pid_idx].strip(),
                    float(row[lat_idx]),
                    float(row[lon_idx]),
                ))
            except (ValueError, IndexError):
                continue

    print(f"  Read {len(pid_lat_lon):,} PSI-points from header pass")

    # pid → egms_points.id Mapping
    pid_to_id = _resolve_point_ids(conn, pid_lat_lon)
    matched = len(pid_to_id)
    unmatched = len(pid_lat_lon) - matched
    print(f"  Matched {matched:,} pids to egms_points.id, "
          f"{unmatched:,} unmatched (these rows will be SKIPPED)")

    # Pass 2 — Zeitreihen-Long-Format einlesen + per COPY in egms_timeseries
    t0 = time.time()
    total = 0
    batch: list[tuple[int, dt.date, float]] = []
    skipped_pids = 0
    skipped_nan = 0

    with open(csv_path, "r", encoding=enc) as f:
        reader = csv.reader(f, delimiter=delim)
        next(reader)  # header
        for row in reader:
            if not row or len(row) <= max(pid_idx, *(c[0] for c in date_cols)):
                continue
            pid = row[pid_idx].strip()
            pid_id = pid_to_id.get(pid)
            if pid_id is None:
                skipped_pids += 1
                continue
            for col_idx, d in date_cols:
                raw = row[col_idx].strip() if col_idx < len(row) else ""
                if not raw or raw.lower() in ("", "nan", "null", "n/a"):
                    skipped_nan += 1
                    continue
                try:
                    disp = float(raw)
                except ValueError:
                    skipped_nan += 1
                    continue
                batch.append((pid_id, d, disp))
                if len(batch) >= batch_rows:
                    total += _copy_timeseries_batch(conn, batch)
                    conn.commit()
                    batch.clear()
                    elapsed = time.time() - t0
                    rate = total / elapsed if elapsed > 0 else 0
                    print(f"    inserted {total:,} rows | {elapsed:.0f}s | "
                          f"{rate:,.0f} rows/s")

    if batch:
        total += _copy_timeseries_batch(conn, batch)
        conn.commit()

    elapsed = time.time() - t0
    print(f"  Final: {total:,} timeseries rows in {elapsed:.0f}s "
          f"(unmatched-pid skips: {skipped_pids:,}, NaN/empty skips: {skipped_nan:,})")
    return {
        "total_rows": total,
        "elapsed_s": elapsed,
        "matched_points": matched,
        "unmatched_points": unmatched,
        "skipped_pids": skipped_pids,
        "skipped_nan": skipped_nan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import EGMS L2b Calibrated time-series CSV → egms_timeseries"
    )
    parser.add_argument("--csv", required=True, help="Path to EGMS L2b CSV file")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    parser.add_argument("--batch", type=int, default=100_000)
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 2

    size_mb = os.path.getsize(args.csv) / (1024 * 1024)
    print(f"Importing {args.csv} ({size_mb:.1f} MB)")
    print(f"DB: {args.db_url.split('@')[-1] if '@' in args.db_url else args.db_url}")

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False
    try:
        result = import_csv(conn, args.csv, batch_rows=args.batch)
        print(f"\n✓ Done: {result}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
