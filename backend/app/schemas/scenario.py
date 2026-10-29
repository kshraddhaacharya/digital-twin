from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from app.utils.datetime_utils import to_utc_iso


class ScenarioPoint(BaseModel):
    timestamp: datetime
    simulated_value: float

    @field_serializer("timestamp", when_used="json")
    def serialize_timestamp(self, dt: Optional[datetime]) -> Optional[str]:
        return to_utc_iso(dt)


class ScenarioSimulateRequest(BaseModel):
    horizon_minutes: Optional[int] = Field(360, ge=30, le=1440, description="Simulation horizon in minutes")
    parameter_name: Optional[str] = Field("trend_damping_pct", description="Hypothetical parameter name")
    parameter_value: float = Field(-25.0, ge=-80.0, le=80.0, description="Parameter adjustment value (e.g. -25% trend slope damping)")
    parameter_unit: Optional[str] = Field("%", description="Parameter unit")


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    baseline_state_version: int
    scenario_type: str
    parameter_name: str
    parameter_value: float
    parameter_unit: str
    mathematical_rule: str
    assumptions: str
    limitations: str
    simulated_trajectory: List[ScenarioPoint]
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(self, dt: Optional[datetime]) -> Optional[str]:
        return to_utc_iso(dt)


class ScenarioComparisonResponse(BaseModel):
    patient_id: str
    baseline_state_version: int
    scenario_a: ScenarioResponse
    scenario_b: ScenarioResponse
    delta_summary: dict
    disclaimer: str

