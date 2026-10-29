from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from app.utils.datetime_utils import to_utc_iso


VALID_UNITS = {
    "heart_rate": ["bpm", "BPM"],
    "systolic_bp": ["mmHg", "mmhg"],
    "diastolic_bp": ["mmHg", "mmhg"],
    "body_temperature": ["degC", "degF", "°C", "°F", "C", "F"],
}

VALUE_BOUNDS = {
    "heart_rate": (30.0, 250.0, "Heart rate must be physiologically plausible (30-250 bpm)"),
    "systolic_bp": (50.0, 260.0, "Systolic blood pressure must be between 50 and 260 mmHg"),
    "diastolic_bp": (30.0, 150.0, "Diastolic blood pressure must be between 30 and 150 mmHg"),
    "body_temperature": (30.0, 45.0, "Body temperature must be between 30.0°C and 45.0°C (or 86-113°F)"),
}

VALID_CONTEXTS = {"resting", "active", "post_exercise", "post_prandial", "clinical", "unspecified"}


class MeasurementCreate(BaseModel):
    timestamp: datetime = Field(..., description="Measurement observation timestamp in ISO 8601 format (UTC)")
    measurement_type: str = Field(..., description="Measurement type, e.g., 'heart_rate'")
    value: float = Field(..., description="Observed numeric value")
    unit: str = Field(..., description="Measurement unit, e.g., 'bpm'")
    source: Optional[str] = Field("manual_entry", description="Source of measurement, e.g., bedside_monitor, csv_upload")
    context: Optional[str] = Field("resting", description="Measurement context: 'resting', 'active', 'post_exercise', 'post_prandial', etc.")

    @field_validator("measurement_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        clean_type = v.strip().lower()
        if clean_type not in VALID_UNITS:
            allowed = ", ".join(VALID_UNITS.keys())
            raise ValueError(f"Unsupported measurement_type '{v}'. Allowed types are: {allowed}")
        return clean_type

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str, info) -> str:
        unit_clean = v.strip()
        m_type = info.data.get("measurement_type")
        if m_type and m_type in VALID_UNITS:
            valid_for_type = VALID_UNITS[m_type]
            if unit_clean not in valid_for_type and unit_clean.lower() not in [u.lower() for u in valid_for_type]:
                raise ValueError(
                    f"Invalid unit '{v}' for measurement_type '{m_type}'. Expected one of: {valid_for_type}"
                )
        return unit_clean

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Optional[str]) -> str:
        if not v:
            return "resting"
        c = v.strip().lower()
        if c not in VALID_CONTEXTS:
            return "resting"
        return c

    @field_validator("value")
    @classmethod
    def validate_bounds(cls, v: float, info) -> float:
        m_type = info.data.get("measurement_type")
        unit = info.data.get("unit", "")
        if m_type and m_type in VALUE_BOUNDS:
            min_v, max_v, msg = VALUE_BOUNDS[m_type]
            if m_type == "body_temperature" and "F" in unit.upper():
                if not (86.0 <= v <= 113.0):
                    raise ValueError(f"Body temperature in °F must be between 86.0°F and 113.0°F. Received: {v}")
                return v
            if not (min_v <= v <= max_v):
                raise ValueError(f"{msg}. Received: {v}")
        return v


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    timestamp: datetime
    measurement_type: str
    value: float
    unit: str
    source: str
    context: str = "resting"
    data_quality: str = "valid"
    is_late_arrival: bool
    created_at: datetime

    @field_serializer("timestamp", "created_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        return to_utc_iso(dt)


class MeasurementBatchUploadResponse(BaseModel):
    success: bool
    patient_id: str
    total_processed: int
    valid_inserted: int
    duplicates_skipped: int
    errors: list[str]
    twin_state_version: Optional[int] = None

