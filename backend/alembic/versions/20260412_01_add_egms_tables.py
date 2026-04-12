"""add egms tables

Revision ID: 20260412_01
Revises:
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260412_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS egms_points (
            id BIGSERIAL PRIMARY KEY,
            geom GEOMETRY(Point, 4326) NOT NULL,
            mean_velocity_mm_yr REAL NOT NULL,
            velocity_std REAL,
            coherence REAL,
            measurement_start DATE,
            measurement_end DATE,
            country CHAR(2) NOT NULL DEFAULT 'DE'
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_egms_points_geom ON egms_points USING GIST (geom)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS egms_timeseries (
            point_id BIGINT NOT NULL REFERENCES egms_points(id) ON DELETE CASCADE,
            measurement_date DATE NOT NULL,
            displacement_mm REAL NOT NULL,
            PRIMARY KEY (point_id, measurement_date)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS egms_timeseries")
    op.execute("DROP INDEX IF EXISTS idx_egms_points_geom")
    op.execute("DROP TABLE IF EXISTS egms_points")
