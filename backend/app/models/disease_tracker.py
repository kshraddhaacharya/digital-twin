from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class HealthCondition(Base):
    __tablename__ = "health_conditions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    condition_name = Column(String(128), nullable=False)
    diagnosed_date = Column(String(32), nullable=True)
    severity = Column(String(32), default="monitoring")  # 'mild', 'moderate', 'severe', 'monitoring'
    status = Column(String(32), default="active")  # 'active', 'managed', 'resolved'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="conditions")
    logs = relationship("ConditionLog", back_populates="condition", cascade="all, delete-orphan")


class ConditionLog(Base):
    __tablename__ = "condition_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    condition_id = Column(Integer, ForeignKey("health_conditions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    log_date = Column(String(32), nullable=False)
    metric_name = Column(String(64), nullable=False)  # e.g., 'Blood Pressure', 'Resting Heart Rate', 'Blood Glucose', 'Symptom Score'
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(32), nullable=False)  # e.g., 'bpm', 'mmHg', 'mg/dL', '1-10'
    symptoms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="condition_logs")
    condition = relationship("HealthCondition", back_populates="logs")

