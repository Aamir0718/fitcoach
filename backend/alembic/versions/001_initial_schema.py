"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-05-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Auth ─────────────────────────────────────────────────────────────────
    op.create_table(
        "auth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # ── Profile ───────────────────────────────────────────────────────────────
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("goal", sa.String(100), nullable=True),
        sa.Column("level", sa.String(20), nullable=True),
        sa.Column("workout_place", sa.String(20), nullable=True),
        sa.Column("days_per_week", sa.Integer(), nullable=True),
        sa.Column("injuries", sa.Text(), nullable=True),
        sa.Column("plays_sport", sa.Boolean(), server_default="false"),
        sa.Column("sport", sa.String(50), nullable=True),
        sa.Column("sport_role", sa.String(100), nullable=True),
        sa.Column("sport_focus", sa.String(100), nullable=True),
        sa.Column("onboarding_complete", sa.Boolean(), server_default="false"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # ── Workouts ──────────────────────────────────────────────────────────────
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("muscle_group", sa.String(100), nullable=True),
        sa.Column("exercises", sa.JSON(), nullable=True),
        sa.Column("exercises_done", sa.Text(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), server_default="false"),
        sa.Column("mode", sa.String(20), nullable=True),
        sa.Column("sport", sa.String(50), nullable=True),
        sa.Column("zone", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_workouts_user_date", "workouts", ["user_id", "date"])

    # ── Set Logs (progressive overload) ───────────────────────────────────────
    op.create_table(
        "set_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=True),
        sa.Column("exercise_name", sa.String(200), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("feedback", sa.String(20), nullable=True),
        sa.Column("is_pr", sa.Boolean(), server_default="false"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_set_logs_user_exercise", "set_logs", ["user_id", "exercise_name"])
    op.create_index("idx_set_logs_user_date", "set_logs", ["user_id", "date"])

    # ── FCM Tokens ────────────────────────────────────────────────────────────
    op.create_table(
        "fcm_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("platform", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "token", name="uq_fcm_user_token"),
    )
    op.create_index("idx_fcm_tokens_user", "fcm_tokens", ["user_id"])

    # ── Weekly Plans ──────────────────────────────────────────────────────────
    op.create_table(
        "weekly_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_weekly_plans_user", "weekly_plans", ["user_id"])

    # ── AI Memory ─────────────────────────────────────────────────────────────
    op.create_table(
        "ai_memory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("muscle_group", sa.String(100), nullable=True),
        sa.Column("feedback", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_memory_user", "ai_memory", ["user_id"])

    # ── Recovery ──────────────────────────────────────────────────────────────
    op.create_table(
        "recovery_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("sleep_quality", sa.Integer(), nullable=True),
        sa.Column("soreness", sa.Integer(), nullable=True),
        sa.Column("stress", sa.Integer(), nullable=True),
        sa.Column("energy", sa.Integer(), nullable=True),
        sa.Column("hrv", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("zone", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_recovery_user_date", "recovery_logs", ["user_id", "date"])

    # ── Progress ──────────────────────────────────────────────────────────────
    op.create_table(
        "weight_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.String(50), nullable=False),
        sa.Column("badge_name", sa.String(100), nullable=False),
        sa.Column("badge_icon", sa.String(10), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "progress_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_private", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── OTP / Refresh tokens ──────────────────────────────────────────────────
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Exercise library ──────────────────────────────────────────────────────
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("mode", sa.String(20), nullable=True),
        sa.Column("sets", sa.Integer(), nullable=True),
        sa.Column("reps", sa.String(20), nullable=True),
        sa.Column("rest", sa.String(20), nullable=True),
        sa.Column("muscle", sa.String(100), nullable=True),
        sa.Column("weight_guide", sa.String(200), nullable=True),
        sa.Column("equipment_required", sa.Boolean(), server_default="false"),
        sa.Column("demo_url", sa.Text(), nullable=True),
        sa.Column("sport", sa.String(50), nullable=True),
        sa.Column("subcategory", sa.String(50), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_exercises_category_gender_mode", "exercises", ["category", "gender", "mode"])
    op.create_index("idx_exercises_sport", "exercises", ["sport"])

    # ── Planned workouts ──────────────────────────────────────────────────────
    op.create_table(
        "planned_workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("workout", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["auth.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_planned_workouts_user_date", "planned_workouts", ["user_id", "date"])


def downgrade() -> None:
    op.drop_table("planned_workouts")
    op.drop_table("exercises")
    op.drop_table("refresh_tokens")
    op.drop_table("otp_codes")
    op.drop_table("progress_photos")
    op.drop_table("badges")
    op.drop_table("weight_logs")
    op.drop_table("recovery_logs")
    op.drop_table("ai_memory")
    op.drop_table("weekly_plans")
    op.drop_table("fcm_tokens")
    op.drop_table("set_logs")
    op.drop_table("workouts")
    op.drop_table("profiles")
    op.drop_table("auth")
