from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Date, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime, date
from app.database import Base


class RecoveryLog(Base):
    __tablename__ = "recovery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth.id", ondelete="CASCADE"), nullable=False)

    date: Mapped[date] = mapped_column(Date, nullable=False)
    sleep_hours: Mapped[float | None] = mapped_column(Float)         # 4-9
    sleep_quality: Mapped[int | None] = mapped_column(Integer)       # 1-5
    fatigue: Mapped[int | None] = mapped_column(Integer)             # 1-5
    soreness: Mapped[int | None] = mapped_column(Integer)            # 1-5
    prev_load: Mapped[int | None] = mapped_column(Integer)           # 1-5
    score: Mapped[int | None] = mapped_column(Integer)               # 0-100
    zone: Mapped[str | None] = mapped_column(String(10))             # green|yellow|red

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["Auth"] = relationship("Auth", back_populates="recovery_logs")

    __table_args__ = (
        Index("idx_recovery_user_date", "user_id", "date"),
    )
