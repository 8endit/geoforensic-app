"""add egms_burst_loaded cache table + burst_id index on egms_points

On-Demand-Loader (egms_burst_loader.py) braucht zwei DB-Strukturen:

1. egms_burst_loaded: Track-Tabelle 'welche Bursts haben wir schon
   geparst + Rows geschrieben'. Damit der Pipeline-Hook bei einer
   neuen Adresse fragen kann 'sind die ueberlappenden Bursts schon im
   System?' bevor er Download triggert.

2. egms_points.burst_id: optional pro PSI-Punkt vermerken zu welchem
   Burst er gehoert. Nicht kritisch fuer den Loader (der filtert per pid),
   aber praktisch fuer Reports/Stats. Sparse — bestehende 11M Punkte
   bekommen den Wert erst wenn ein Burst sie zum ersten Mal parsed.

Revision ID: 20260505_03
Revises: 20260505_02
Create Date: 2026-05-05
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260505_03"
down_revision: Union[str, Sequence[str], None] = "20260505_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS egms_burst_loaded ("
        "  burst_id VARCHAR(64) PRIMARY KEY,"
        "  loaded_at TIMESTAMPTZ NOT NULL,"
        "  row_count INTEGER NOT NULL DEFAULT 0,"
        "  source_qid_hash BIGINT"
        ")"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_egms_burst_loaded_loaded_at "
        "ON egms_burst_loaded (loaded_at DESC)"
    )
    op.execute(
        "ALTER TABLE egms_points "
        "ADD COLUMN IF NOT EXISTS burst_id VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_egms_points_burst_id "
        "ON egms_points (burst_id) WHERE burst_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_egms_points_burst_id")
    op.execute("ALTER TABLE egms_points DROP COLUMN IF EXISTS burst_id")
    op.execute("DROP INDEX IF EXISTS idx_egms_burst_loaded_loaded_at")
    op.execute("DROP TABLE IF EXISTS egms_burst_loaded")
