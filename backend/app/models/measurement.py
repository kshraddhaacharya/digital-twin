from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    measurement_type = Column(String(64), nullable=False, index=True)  # e.g., 'heart_rate', 'systolic_bp'
    value = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)  # e.g., 'bpm', 'mmHg'
    source = Column(String(64), nullable=False, default="manual")  # e.g., 'synthetic', 'csv_upload', 'manual'
    context = Column(String(32), nullable=False, default="resting")  # 'resting', 'active', 'post_exercise', 'post_prandial', 'clinical'
    data_quality = Column(String(32), nullable=False, default="valid")  # 'valid', 'outlier', 'interpolated', 'suspect'
    is_late_arrival = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="measurements")

    __table_args__ = (
        UniqueConstraint("patient_id", "measurement_type", "timestamp", name="uq_patient_measurement_time"),
        Index("ix_patient_type_time", "patient_id", "measurement_type", "timestamp"),
    )

