from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Date, Text, Index
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
