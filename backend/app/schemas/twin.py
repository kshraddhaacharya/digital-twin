from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from app.utils.datetime_utils import to_utc_iso


class TwinStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    state_version: int
    timestamp_latest_observation: datetime
    last_processed_measurement_id: Optional[int] = None
    
    # Raw latest observation
    latest_heart_rate: float
    measurement_context: str = "resting"
    
    # Inferred state features
    rolling_mean_60m: Optional[float] = None
    rolling_std_60m: Optional[float] = None
    trend_slope_per_hour: Optional[float] = None
    circadian_phase_estimate: Optional[float] = None
    physiological_variability_index: Optional[float] = None
    vital_status: str = "normal"
    
    # Model & Provenance
    model_version: str = "1.0.0"
    data_quality_status: str = "good"
    latest_forecast_time: Optional[datetime] = None
    previous_state_hash: Optional[str] = None

    # Web3 On-Chain Attestation fields
    attestation_status: str = "PENDING"
    on_chain_tx_hash: Optional[str] = None
    on_chain_block_number: Optional[int] = None
    state_hash_sha256: Optional[str] = None
    ipfs_cid: Optional[str] = None
    contract_address: Optional[str] = None

    # Metadata
    data_freshness_seconds: float = 0.0
    is_active_version: bool = True
    created_at: datetime

    @field_serializer("timestamp_latest_observation", "latest_forecast_time", "created_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        return to_utc_iso(dt)


class TwinUpdateResult(BaseModel):
    success: bool
    patient_id: str
    previous_state_version: int
    new_state_version: int
    updated_at: datetime
    latest_measurement_value: float
    stale_forecasts_invalidated: int
    twin_state: TwinStateResponse
    message: str

    @field_serializer("updated_at", when_used="json")
    def serialize_updated_at(self, dt: Optional[datetime]) -> Optional[str]:
        return to_utc_iso(dt)

