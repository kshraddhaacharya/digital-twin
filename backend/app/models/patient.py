from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(32), nullable=False)
    baseline_heart_rate = Column(Float, nullable=False, default=70.0)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    profile_version = Column(Integer, nullable=False, default=1)
    medical_notes = Column(Text, nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    wallet_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    measurements = relationship("Measurement", back_populates="patient", cascade="all, delete-orphan", order_by="Measurement.timestamp")
    twin_states = relationship("TwinState", back_populates="patient", cascade="all, delete-orphan", order_by="TwinState.state_version")
    forecasts = relationship("Forecast", back_populates="patient", cascade="all, delete-orphan", order_by="Forecast.created_at.desc()")
    scenarios = relationship("Scenario", back_populates="patient", cascade="all, delete-orphan", order_by="Scenario.created_at.desc()")
    evaluations = relationship("ModelEvaluation", back_populates="patient", cascade="all, delete-orphan")

