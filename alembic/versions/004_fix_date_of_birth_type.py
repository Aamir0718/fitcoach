"""Fix date_of_birth column type: DATE → VARCHAR(20)

Migration 001 created date_of_birth as sa.Date() but the Profile model
stores it as String(20) (ISO date string like "1995-08-14").
PostgreSQL refuses to cast VARCHAR → DATE, crashing every signup.

Revision ID: 004
Revises: 003
Create Date: 2026-05-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast existing DATE values to text so no data is lost.
    # USING clause converts DATE → VARCHAR safely.
    op.execute("""
        ALTER TABLE profiles
        ALTER COLUMN date_of_birth TYPE VARCHAR(20)
        USING date_of_birth::text;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE profiles
        ALTER COLUMN date_of_birth TYPE DATE
        USING date_of_birth::date;
    """)
