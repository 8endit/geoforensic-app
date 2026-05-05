"""add egms_pid to egms_points (originale EGMS-Punkt-ID fuer L2b-Join)

EGMS L2b-Zeitreihen-CSVs haben pro Zeile eine `pid` (z.B.
'E48N32_AAJSx'), die identisch mit der pid in der L3-Velocity-CSV ist
mit der wir egms_points befuellt haben — aber damals hatte das
import-Skript die pid weggeworfen, nur lat/lon/velocity behalten.

Damit der L2b-TS-Import die Zeitreihen-Zeilen einem egms_points.id-FK
zuordnen kann, brauchen wir die EGMS-pid als Brueckenfeld in der
L3-Tabelle. Re-Import der L3-Daten (mit pid behalten) wird zukuenftig
diese Spalte befuellen; bestehende Zeilen bleiben pid=NULL und werden
fuer L2b-Match per Spatial-Lookup auf <2 m gefallback.

Revision ID: 20260505_02
Revises: 20260505_01
Create Date: 2026-05-05
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260505_02"
down_revision: Union[str, Sequence[str], None] = "20260505_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE egms_points "
        "ADD COLUMN IF NOT EXISTS egms_pid VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_egms_points_egms_pid "
        "ON egms_points (egms_pid) WHERE egms_pid IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_egms_points_egms_pid")
    op.execute("ALTER TABLE egms_points DROP COLUMN IF EXISTS egms_pid")
