"""add functional GIST index on egms_points (geom::geography)

Without this index, ST_DWithin(geom::geography, ..., radius_m) cannot
use the existing GIST index on geom (geometry, SRID 4326) — Postgres
falls back to a Parallel Seq Scan over the whole table (11 Mio Rows
in 5/2026 = 12 s pro Query). Mit funktionalem Index auf der geography-
Cast-Variante: 23 ms — ~560x schneller.

NOTE: built without CONCURRENTLY because Alembic transactions don't
allow it. Initial build on prod (11 Mio Rows) dauert ~3-4 min und
hält dabei einen Schreib-Lock auf egms_points. Inserts in die
Tabelle laufen aber nur von Bulk-Import-Scripts (egms ingestion),
nicht aus dem Live-Lead-Flow — also kein Risiko für customer-facing
Requests.

Revision ID: 20260505_01
Revises: 20260503_01
Create Date: 2026-05-05
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260505_01"
down_revision: Union[str, Sequence[str], None] = "20260503_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_egms_points_geom_geog "
        "ON egms_points USING GIST ((geom::geography))"
    )
    # Refresh stats so the planner sees the new index immediately.
    op.execute("ANALYZE egms_points")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_egms_points_geom_geog")
