from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class PeriodCycle(Base):
    __tablename__ = "period_cycles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    start_date = Column(String(32), nullable=False)
    end_date = Column(String(32), nullable=True)
    cycle_length_days = Column(Integer, default=28, nullable=False)
    period_length_days = Column(Integer, default=5, nullable=False)
    flow_intensity = Column(String(32), default="medium")  # 'light', 'medium', 'heavy', 'spotting'
    symptoms = Column(Text, nullable=True)  # JSON or comma-separated symptoms (cramps, bloating, mood, etc.)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="cycles")

