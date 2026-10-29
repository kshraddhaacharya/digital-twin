from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_state_version = Column(Integer, nullable=False, index=True)
    scenario_type = Column(String(64), nullable=False)  # 'Scenario_A_Current_Trajectory' or 'Scenario_B_Hypothetical_Condition'
    
    # Transparent parameter documentation
    parameter_name = Column(String(64), nullable=False)
    parameter_value = Column(Float, nullable=False)
    parameter_unit = Column(String(32), nullable=False)
    mathematical_rule = Column(Text, nullable=False)
    assumptions = Column(Text, nullable=False)
    limitations = Column(Text, nullable=False)
    
    # Output trajectory
    simulated_trajectory = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    patient = relationship("Patient", back_populates="scenarios")

