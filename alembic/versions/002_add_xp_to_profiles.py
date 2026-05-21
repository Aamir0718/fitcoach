"""Add xp column to profiles (idempotent — xp may already exist from migration 001)

Revision ID: 002
Revises: 001
Create Date: 2026-05-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS so this is safe to run even if xp
    # was already created by migration 001's CREATE TABLE statement.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'profiles' AND column_name = 'xp'
            ) THEN
                ALTER TABLE profiles ADD COLUMN xp INTEGER NOT NULL DEFAULT 0;
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.drop_column("profiles", "xp")
