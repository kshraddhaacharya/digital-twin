from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Health & Profile fields
    age = Column(Integer, nullable=True)
    date_of_birth = Column(String(32), nullable=True)
    gender = Column(String(32), nullable=True, default="Prefer not to say")
    height = Column(Float, nullable=True)  # in cm
    body_weight = Column(Float, nullable=True)  # in kg
    profile_version = Column(Integer, nullable=False, default=1)
    existing_conditions = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    emergency_contact = Column(String(128), nullable=True)
    profile_photo = Column(Text, nullable=True)
    health_notes = Column(Text, nullable=True)

    # Linked Digital Twin patient ID
    patient_id = Column(String(64), nullable=False, unique=True, index=True)

    # Relationships
    reports = relationship("MedicalReport", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("UserVideo", back_populates="user", cascade="all, delete-orphan")
    conditions = relationship("HealthCondition", back_populates="user", cascade="all, delete-orphan")
    condition_logs = relationship("ConditionLog", back_populates="user", cascade="all, delete-orphan")
    cycles = relationship("PeriodCycle", back_populates="user", cascade="all, delete-orphan")

