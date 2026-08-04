from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, JSON, Date, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime, date
from app.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)

    date: Mapped[date] = mapped_column(Date, nullable=False)
    muscle_group: Mapped[str | None] = mapped_column(String(100))
    exercises: Mapped[list | None] = mapped_column(JSON)             # full exercise list with sets/reps
    exercises_done: Mapped[str | None] = mapped_column(Text)         # comma-separated names
    duration: Mapped[int | None] = mapped_column(Integer)            # minutes
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str | None] = mapped_column(String(20))             # gym | home | sport
    sport: Mapped[str | None] = mapped_column(String(50))
    zone: Mapped[str | None] = mapped_column(String(10))             # green | yellow | red
    notes: Mapped[str | None] = mapped_column(Text)
    
    # Analytics fields
    total_sets: Mapped[int | None] = mapped_column(Integer)          # Total sets completed
    total_reps: Mapped[int | None] = mapped_column(Integer)          # Total reps completed
    calories_estimate: Mapped[float | None] = mapped_column(Float)    # Estimated calories burned
    completion_percentage: Mapped[float | None] = mapped_column(Float) # % of exercises completed
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="workouts")

    __table_args__ = (
        Index("idx_workouts_user_date", "user_id", "date"),
    )


class PlannedWorkout(Base):
    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    workout: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_planned_workouts_user_date", "user_id", "date"),
    )


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    mode: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_weekly_plans_user", "user_id"),
    )


class AIMemory(Base):
    __tablename__ = "ai_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    muscle_group: Mapped[str | None] = mapped_column(String(100))
    feedback: Mapped[str | None] = mapped_column(String(50))         # easy | hard | good
    notes: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_ai_memory_user", "user_id"),
    )


class SetLog(Base):
    """Per-set weight/rep/feedback logging — enables progressive overload tracking."""
    __tablename__ = "set_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    workout_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("workouts.id", ondelete="SET NULL"))
    exercise_name: Mapped[str] = mapped_column(String(200), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(String(20))  # easy | perfect | hard
    is_pr: Mapped[bool] = mapped_column(Boolean, default=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_set_logs_user_exercise", "user_id", "exercise_name"),
        Index("idx_set_logs_user_date", "user_id", "date"),
    )


class FCMToken(Base):
    """Firebase Cloud Messaging tokens for push notifications."""
    __tablename__ = "fcm_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(10))  # android | ios | web
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_fcm_tokens_user", "user_id"),
        UniqueConstraint("user_id", "token", name="uq_fcm_user_token"),
    )


class Exercise(Base):
    """Exercise library — moved out of hardcoded Python dicts."""
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))         # push|pull|legs|upper|lower|full_body|core|cardio
    gender: Mapped[str | None] = mapped_column(String(10))           # male|female|any
    mode: Mapped[str | None] = mapped_column(String(20))             # gym|home|sport|any
    sets: Mapped[int | None] = mapped_column(Integer)
    reps: Mapped[str | None] = mapped_column(String(20))
    rest: Mapped[str | None] = mapped_column(String(20))
    muscle: Mapped[str | None] = mapped_column(String(100))
    weight_guide: Mapped[str | None] = mapped_column(String(200))
    equipment_required: Mapped[bool] = mapped_column(Boolean, default=False)
    demo_url: Mapped[str | None] = mapped_column(Text)
    sport: Mapped[str | None] = mapped_column(String(50))            # null for non-sport
    subcategory: Mapped[str | None] = mapped_column(String(50))      # power|mobility|agility etc for sport
    tags: Mapped[list | None] = mapped_column(JSON)                  # ["beginner", "compound", "glute"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_exercises_category_gender_mode", "category", "gender", "mode"),
        Index("idx_exercises_sport", "sport"),
    )
