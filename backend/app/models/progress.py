from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Date, Text, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime, date
from app.database import Base


class WeightLog(Base):
    __tablename__ = "weight_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)     # kg
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="weight_logs")

    __table_args__ = (
        Index("idx_weight_logs_user_date", "user_id", "date"),
    )


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    badge_id: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(10), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="badges")

    __table_args__ = (
        Index("idx_badges_user", "user_id"),
    )


class ProgressPhoto(Base):
    """Before/after transformation photos."""
    __tablename__ = "progress_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float | None] = mapped_column(Float)              # kg at time of photo
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
    is_private: Mapped[bool] = mapped_column(Integer, default=True)  # private by default
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="progress_photos")

    __table_args__ = (
        Index("idx_progress_photos_user_date", "user_id", "date"),
    )


class NutritionLog(Base):
    """Nutrition logging for meals and food scans."""
    __tablename__ = "nutrition_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_name: Mapped[str | None] = mapped_column(String(200))
    calories: Mapped[float | None] = mapped_column(Float)
    protein: Mapped[float | None] = mapped_column(Float)            # grams
    carbs: Mapped[float | None] = mapped_column(Float)              # grams
    fats: Mapped[float | None] = mapped_column(Float)                # grams
    source: Mapped[str | None] = mapped_column(String(20))           # text | photo | manual
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="nutrition_logs")

    __table_args__ = (
        Index("idx_nutrition_logs_user_date", "user_id", "date"),
    )


class Streak(Base):
    """Track current and longest streaks."""
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), unique=True, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_workout_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="streak")

    __table_args__ = (
        Index("idx_streaks_user", "user_id"),
    )


class PersonalRecord(Base):
    """Track personal records for exercises."""
    __tablename__ = "personal_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(200), nullable=False)
    best_weight_kg: Mapped[float | None] = mapped_column(Float)
    best_reps: Mapped[int | None] = mapped_column(Integer)
    best_weight_date: Mapped[date | None] = mapped_column(Date)
    best_reps_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="personal_records")

    __table_args__ = (
        Index("idx_pr_user_exercise", "user_id", "exercise_name"),
    )


class ActivityLog(Base):
    """Unified activity timeline for workouts, nutrition, recovery."""
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # workout | nutrition | recovery | weight
    activity_id: Mapped[int | None] = mapped_column(Integer)               # Reference to workout_id, nutrition_log_id, etc.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    meta_data: Mapped[dict | None] = mapped_column(JSON)                  # Additional data like duration, calories, etc.
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="activity_logs")

    __table_args__ = (
        Index("idx_activity_logs_user_date", "user_id", "date"),
    )
