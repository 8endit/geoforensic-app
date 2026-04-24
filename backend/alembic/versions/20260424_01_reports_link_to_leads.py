"""link reports to leads — persist lead-flow reports in the reports table

Background: the lead flow (bodenbericht.de teaser) used to compute and mail
the PDF without writing anything to the reports table. That left no audit
spur, no way to tell what ampel a given lead got, and no foundation for the
paid flow which needs a report row to sell. This migration makes the reports
table usable for both paths:

  * lead_id nullable FK to leads.id (new)     — set by the free lead flow
  * user_id nullable (was NOT NULL)          — stays required for the paid
                                                flow, but lead-flow reports
                                                do not have a user

Downstream code will insert a reports row after every successful PDF render
in the lead pipeline. A CHECK-equivalent is not enforced at the DB level
(intentionally — we would rather have a row with both nulls than lose the
audit spur because one branch forgot to set one of them).

Revision ID: 20260424_01
Revises: 20260416_01
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260424_01"
down_revision: Union[str, Sequence[str], None] = "20260416_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # user_id no longer required — lead-flow reports have no user.
    op.execute("ALTER TABLE reports ALTER COLUMN user_id DROP NOT NULL")

    # Add lead_id column + FK + index. Guards make the migration idempotent
    # in case it was partially applied. Postgres does not support
    # ADD CONSTRAINT IF NOT EXISTS, so we gate that one behind a DO block.
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS lead_id UUID")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_reports_lead_id'
                  AND table_name = 'reports'
            ) THEN
                ALTER TABLE reports
                ADD CONSTRAINT fk_reports_lead_id
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL;
            END IF;
        END$$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_lead_id ON reports (lead_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_reports_lead_id")
    op.execute("ALTER TABLE reports DROP CONSTRAINT IF EXISTS fk_reports_lead_id")
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS lead_id")
    # Restoring user_id NOT NULL only makes sense if no lead-flow rows exist
    # anymore; otherwise we would need to delete them first. We just leave
    # the column nullable on downgrade — that is the safer default.
