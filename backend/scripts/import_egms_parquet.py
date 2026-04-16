"""Import EGMS Parquet files from F:/geoforensic-data/egms/ into PostGIS.

Usage:
    python backend/scripts/import_egms_parquet.py --country NL
    python backend/scripts/import_egms_parquet.py --country DE
    python backend/scripts/import_egms_parquet.py --country NL --country DE
"""

import argparse
import glob
import os
import time

import psycopg2
import pyarrow.parquet as pq

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/geoforensic")
EGMS_BASE = os.getenv("EGMS_BASE", "F:/geoforensic-data/egms")
BATCH_SIZE = 5000


def import_country(conn, country: str) -> int:
    store_dir = os.path.join(EGMS_BASE, country)
    files = sorted(glob.glob(os.path.join(store_dir, "points_*.parquet")))
    if not files:
        print(f"  No parquet files found in {store_dir}")
        return 0

    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    conn.commit()

    total = 0
    t0 = time.time()

    for fpath in files:
        fname = os.path.basename(fpath)
        t = pq.read_table(fpath)
        df = t.to_pandas()

        rows = []
        for _, r in df.iterrows():
            rows.append((
                float(r["lon"]), float(r["lat"]),
                float(r["mean_velocity_mm_yr"]),
                float(r["mean_velocity_std"]) if r.get("mean_velocity_std") is not None else None,
                None,  # coherence (not in EGMS parquet)
                country,
            ))
            if len(rows) >= BATCH_SIZE:
                _insert_batch(cur, rows)
                total += len(rows)
                rows = []

        if rows:
            _insert_batch(cur, rows)
            total += len(rows)

        conn.commit()
        elapsed = time.time() - t0
        rate = total / elapsed if elapsed > 0 else 0
        print(f"  {fname}: +{len(df):,} | Total: {total:,} | {elapsed:.0f}s | {rate:.0f} rows/s")

    return total


def _insert_batch(cur, rows: list) -> None:
    args = ",".join(
        cur.mogrify(
            "(ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,%s,%s,%s)", row
        ).decode()
        for row in rows
    )
    cur.execute(
        f"INSERT INTO egms_points (geom, mean_velocity_mm_yr, velocity_std, coherence, country) VALUES {args}"
    )


def main():
    parser = argparse.ArgumentParser(description="Import EGMS parquet into PostGIS")
    parser.add_argument("--country", action="append", required=True, help="Country code (NL, DE)")
    parser.add_argument("--clear", action="store_true", help="Delete existing data for country before import")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    for country in args.country:
        country = country.upper()
        print(f"\n{'='*60}")
        print(f"Importing {country} from {EGMS_BASE}/{country}/")
        print(f"{'='*60}")

        if args.clear:
            cur = conn.cursor()
            cur.execute("DELETE FROM egms_points WHERE country = %s", (country,))
            deleted = cur.rowcount
            conn.commit()
            print(f"  Cleared {deleted:,} existing {country} rows")

        total = import_country(conn, country)
        print(f"  => {total:,} rows imported for {country}")

    # Final count
    cur = conn.cursor()
    cur.execute("SELECT country, COUNT(*) FROM egms_points GROUP BY country ORDER BY country")
    print(f"\n{'='*60}")
    print("Final state:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    cur.execute("SELECT COUNT(*) FROM egms_points")
    print(f"  TOTAL: {cur.fetchone()[0]:,} rows")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
