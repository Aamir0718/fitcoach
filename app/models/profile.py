from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Basic info
    name: Mapped[str | None] = mapped_column(String(100))
    date_of_birth: Mapped[str | None] = mapped_column(String(20))   # ISO date string
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(10))           # male | female

    # Body metrics
    height: Mapped[float | None] = mapped_column(Float)             # cm
    weight: Mapped[float | None] = mapped_column(Float)             # kg

    # Training profile
    goal: Mapped[str | None] = mapped_column(String(50))
    # fat_loss | muscle_gain | strength | general_fitness | toned_body | glute_growth | lean_physique | hourglass
    level: Mapped[str | None] = mapped_column(String(20))           # beginner | intermediate | advanced
    workout_place: Mapped[str | None] = mapped_column(String(20))   # gym | home
    days_per_week: Mapped[int | None] = mapped_column(Integer)
    injuries: Mapped[str | None] = mapped_column(String(500))

    # Sport mode
    plays_sport: Mapped[bool] = mapped_column(Boolean, default=False)
    sport: Mapped[str | None] = mapped_column(String(50))           # cricket | football | running
    sport_role: Mapped[str | None] = mapped_column(String(100))     # batsman | bowler etc
    sport_focus: Mapped[str | None] = mapped_column(String(100))    # batting | bowling | fielding
    sport_position: Mapped[str | None] = mapped_column(String(100))
    match_frequency: Mapped[str | None] = mapped_column(String(50)) # weekly | bi-weekly | monthly
    sport_injuries: Mapped[str | None] = mapped_column(String(500))
    bowling_type: Mapped[str | None] = mapped_column(String(50))    # cricket-specific

    # XP / Gamification
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Onboarding state
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    sport_onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Preferences (stored as JSON)
    preferences: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # e.g. {"theme": "galaxy", "units": "metric", "notifications_enabled": true}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["Auth"] = relationship("Auth", back_populates="profile")

    @property
    def bmi(self) -> float | None:
        if self.height and self.weight:
            return round(self.weight / ((self.height / 100) ** 2), 1)
        return None

    @property
    def active_mode(self) -> str:
        if self.plays_sport and self.sport:
            return "sport"
        return self.workout_place or "gym"
