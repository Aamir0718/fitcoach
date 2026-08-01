"""Fix column name mismatches between migration 001 and current models.

Migration 001 used old column names that no longer match the SQLAlchemy models:
  - otp_codes.code  → otp_codes.otp_hash  (SHA-256, needs String(64))
  - refresh_tokens.token → refresh_tokens.token_hash (needs String(64) + unique)
  - refresh_tokens.revoked (not in model — drop it)
  - profiles missing: sport_position, match_frequency, sport_injuries,
    bowling_type, sport_onboarding_complete, preferences

Revision ID: 003
Revises: 002
Create Date: 2026-05-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check information_schema for column existence (works on PostgreSQL)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :i"
    ), {"i": index_name})
    return result.fetchone() is not None


# ─────────────────────────────────────────────────────────────────────────────
def upgrade() -> None:

    # ── 1. Fix otp_codes ─────────────────────────────────────────────────────
    # Old column: code VARCHAR(10)
    # New column: otp_hash VARCHAR(64) (SHA-256 hex digest)

    if _column_exists("otp_codes", "code") and not _column_exists("otp_codes", "otp_hash"):
        # Add new column (nullable while we migrate)
        op.add_column("otp_codes", sa.Column("otp_hash", sa.String(64), nullable=True))
        # No data to migrate — fresh DB.  Drop old column.
        op.drop_column("otp_codes", "code")
        # Make it NOT NULL now that the old column is gone
        op.alter_column("otp_codes", "otp_hash", nullable=False)

    elif not _column_exists("otp_codes", "otp_hash"):
        # Neither column exists (unusual) — add otp_hash fresh
        op.add_column("otp_codes", sa.Column("otp_hash", sa.String(64), nullable=False))

    # Add index if missing
    if not _index_exists("idx_otp_email_purpose"):
        op.create_index("idx_otp_email_purpose", "otp_codes", ["email", "purpose"])

    # ── 2. Fix refresh_tokens ────────────────────────────────────────────────
    # Old columns: token VARCHAR(500), revoked BOOLEAN
    # New column : token_hash VARCHAR(64) UNIQUE NOT NULL

    if _column_exists("refresh_tokens", "token") and not _column_exists("refresh_tokens", "token_hash"):
        # Add token_hash (nullable while we do the swap)
        op.add_column("refresh_tokens", sa.Column("token_hash", sa.String(64), nullable=True))
        # Drop old columns (no real data to preserve)
        op.drop_column("refresh_tokens", "token")
        if _column_exists("refresh_tokens", "revoked"):
            op.drop_column("refresh_tokens", "revoked")
        # Make NOT NULL
        op.alter_column("refresh_tokens", "token_hash", nullable=False)

    elif not _column_exists("refresh_tokens", "token_hash"):
        op.add_column("refresh_tokens", sa.Column("token_hash", sa.String(64), nullable=False))
        if _column_exists("refresh_tokens", "revoked"):
            op.drop_column("refresh_tokens", "revoked")

    # Unique index on token_hash
    if not _index_exists("idx_refresh_tokens_token_hash"):
        op.create_index("idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # User index (query performance)
    if not _index_exists("idx_refresh_tokens_user_id"):
        op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ── 3. Add missing profile columns ───────────────────────────────────────
    profile_additions = [
        ("sport_position",           sa.String(100),  None,    True),
        ("match_frequency",          sa.String(50),   None,    True),
        ("sport_injuries",           sa.String(500),  None,    True),
        ("bowling_type",             sa.String(50),   None,    True),
        ("sport_onboarding_complete",sa.Boolean(),    "false", False),
        ("preferences",              sa.JSON(),       None,    True),
    ]

    for col_name, col_type, server_default, nullable in profile_additions:
        if not _column_exists("profiles", col_name):
            op.add_column(
                "profiles",
                sa.Column(col_name, col_type,
                          server_default=server_default,
                          nullable=nullable)
            )


# ─────────────────────────────────────────────────────────────────────────────
def downgrade() -> None:
    # Reverse profile columns
    for col_name in ("preferences", "sport_onboarding_complete",
                     "bowling_type", "sport_injuries",
                     "match_frequency", "sport_position"):
        if _column_exists("profiles", col_name):
            op.drop_column("profiles", col_name)

    # Reverse refresh_tokens
    if _column_exists("refresh_tokens", "token_hash"):
        op.drop_index("idx_refresh_tokens_token_hash", table_name="refresh_tokens")
        op.drop_column("refresh_tokens", "token_hash")
        op.add_column("refresh_tokens", sa.Column("token", sa.String(500), nullable=False))
        op.add_column("refresh_tokens", sa.Column("revoked", sa.Boolean(), server_default="false"))

    # Reverse otp_codes
    if _column_exists("otp_codes", "otp_hash"):
        op.drop_index("idx_otp_email_purpose", table_name="otp_codes")
        op.drop_column("otp_codes", "otp_hash")
        op.add_column("otp_codes", sa.Column("code", sa.String(10), nullable=False))
