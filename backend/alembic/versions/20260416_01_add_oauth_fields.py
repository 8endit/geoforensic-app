"""add oauth fields to users table

Revision ID: 20260416_01
Revises: 20260412_01
Create Date: 2026-04-16
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260416_01"
down_revision: Union[str, Sequence[str], None] = "20260412_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) NOT NULL DEFAULT 'email'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider_id VARCHAR(255)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_provider_id "
        "ON users (auth_provider, auth_provider_id) "
        "WHERE auth_provider_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_provider_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS auth_provider_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS auth_provider")
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.execute("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL")
