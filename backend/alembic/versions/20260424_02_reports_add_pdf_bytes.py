"""add pdf_bytes column to reports for historically-exact re-download

C1 persisted the structured report data (ampel, score, counts, etc.) but
not the rendered PDF itself. C2 adds pdf_bytes as a nullable BYTEA column
so the admin PDF-download endpoint can serve the original bytes that were
mailed to the recipient — no re-render needed, no drift over time as the
template code evolves.

Rows that predate this column or where PDF rendering failed remain with
pdf_bytes=NULL; the admin endpoint returns 404 in that case.

Revision ID: 20260424_02
Revises: 20260424_01
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260424_02"
down_revision: Union[str, Sequence[str], None] = "20260424_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS pdf_bytes BYTEA")


def downgrade() -> None:
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS pdf_bytes")
