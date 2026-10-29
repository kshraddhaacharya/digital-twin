from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.connection import Base


class TwinState(Base):
    __tablename__ = "twin_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    state_version = Column(Integer, nullable=False, index=True)
    timestamp_latest_observation = Column(DateTime, nullable=False)
    last_processed_measurement_id = Column(Integer, nullable=True)

    # Latest observed values
    latest_heart_rate = Column(Float, nullable=False)
    measurement_context = Column(String(32), nullable=False, default="resting")

    # Inferred physiological features (distinct from raw observations)
    rolling_mean_60m = Column(Float, nullable=True)
    rolling_std_60m = Column(Float, nullable=True)
    trend_slope_per_hour = Column(Float, nullable=True)  # in bpm/hr
    circadian_phase_estimate = Column(Float, nullable=True)  # diurnal baseline estimate
    physiological_variability_index = Column(Float, nullable=True)
    vital_status = Column(String(32), nullable=False, default="normal")  # normal, elevated, tachycardia, bradycardia
    
    # Model & Provenance
    model_version = Column(String(32), nullable=False, default="1.0.0")
    data_quality_status = Column(String(64), nullable=False, default="good")  # good, irregular_intervals, stale_data, insufficient_history
    latest_forecast_time = Column(DateTime, nullable=True)
    previous_state_hash = Column(String(64), nullable=True)

    # Web3 On-Chain Anchoring & IPFS Cryptographic Attestation
    attestation_status = Column(String(32), nullable=False, default="PENDING")  # VERIFIED, PENDING, FAILED, UNAVAILABLE, SIMULATED
    on_chain_tx_hash = Column(String(128), nullable=True)
    on_chain_block_number = Column(Integer, nullable=True)
    state_hash_sha256 = Column(String(64), nullable=True)
    ipfs_cid = Column(String(128), nullable=True)
    contract_address = Column(String(64), nullable=True)

    # State metadata
    data_freshness_seconds = Column(Float, nullable=False, default=0.0)
    is_active_version = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="twin_states")

    __table_args__ = (
        Index("ix_patient_version", "patient_id", "state_version"),
    )

