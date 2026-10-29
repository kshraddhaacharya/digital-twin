from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    twin_state_version = Column(Integer, nullable=False, index=True)
    last_observation_timestamp = Column(DateTime, nullable=False)
    
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), nullable=False, default="1.0.0")
    forecast_horizon_minutes = Column(Integer, nullable=False, default=360)
    
    # Serialized trajectory: list of dicts with timestamp, predicted_value, lower_bound, upper_bound
    predicted_trajectory = Column(JSON, nullable=False)
    
    # Freshness / invalidation
    is_stale = Column(Boolean, nullable=False, default=False, index=True)
    stale_reason = Column(String(256), nullable=True)
    quality_warnings = Column(JSON, nullable=True, default=list)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    patient = relationship("Patient", back_populates="forecasts")

    __table_args__ = (
        Index("ix_patient_forecast_state", "patient_id", "twin_state_version"),
    )

