"""add confirmation_token + confirmed_at to leads for double-opt-in

The premium-waitlist surface collects marketing consent for a future
product launch. Per UWG § 7 Abs. 2 Nr. 2 we need a verifiable double-opt-in
trail: lead is created with a confirmation_token, confirmation email is
sent, user clicks the link → confirmed_at is set and the token cleared.

Existing leads keep both columns NULL (i.e. unconfirmed but also
not waitlist-bound — they were transactional report requests where
DOI is not legally required).

Revision ID: 20260503_01
Revises: 20260424_02
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260503_01"
down_revision: Union[str, Sequence[str], None] = "20260424_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS confirmation_token VARCHAR(64)")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_leads_confirmation_token "
        "ON leads (confirmation_token) WHERE confirmation_token IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_leads_confirmation_token")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS confirmed_at")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS confirmation_token")
