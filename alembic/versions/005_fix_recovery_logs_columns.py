"""Fix recovery_logs column mismatches.

Migration 001 created recovery_logs with: stress, energy, hrv, notes
Current model expects:                   fatigue, prev_load
(stress/energy/hrv/notes stay — extra columns don't break SQLAlchemy)

Revision ID: 005
Revises: 004
Create Date: 2026-05-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    return result.fetchone() is not None


def upgrade() -> None:
    if not _col_exists("recovery_logs", "fatigue"):
        op.add_column("recovery_logs", sa.Column("fatigue", sa.Integer(), nullable=True))

    if not _col_exists("recovery_logs", "prev_load"):
        op.add_column("recovery_logs", sa.Column("prev_load", sa.Integer(), nullable=True))


def downgrade() -> None:
    if _col_exists("recovery_logs", "prev_load"):
        op.drop_column("recovery_logs", "prev_load")
    if _col_exists("recovery_logs", "fatigue"):
        op.drop_column("recovery_logs", "fatigue")
