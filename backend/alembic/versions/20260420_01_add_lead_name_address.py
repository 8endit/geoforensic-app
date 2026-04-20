"""add name and address fields to leads table

Revision ID: 20260420_01
Revises: 20260416_01
Create Date: 2026-04-20

Stefan feature batch:
- first_name + last_name as required fields on the free report form
- street + house_number as separate fields so the geocoder always gets
  an unambiguous address (no more "Menschen heulen" when the house
  number is missing)

Columns are nullable at the DB level so existing leads from the
premium-waitlist flow (email-only) stay valid. Application-level
validation enforces required-ness for quiz/landing sources.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260420_01"
down_revision: Union[str, Sequence[str], None] = "20260416_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS first_name VARCHAR(120)")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_name VARCHAR(120)")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS street VARCHAR(255)")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS house_number VARCHAR(20)")


def downgrade() -> None:
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS house_number")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS street")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS last_name")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS first_name")
