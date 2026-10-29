from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from app.utils.datetime_utils import to_utc_iso


class EvaluationRequest(BaseModel):
    test_split_ratio: float = Field(0.2, ge=0.1, le=0.4, description="Held-out chronological test ratio (e.g., 0.2 = last 20% of data)")


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    model_name: str
    evaluation_period_start: datetime
    evaluation_period_end: datetime
    train_samples: int
    test_samples: int
    mae: float
    rmse: float
    baseline_mae: float
    baseline_rmse: float
    mae_improvement_pct: float
    is_synthetic_data: bool
    disclaimer: str
    created_at: datetime

    @field_serializer("evaluation_period_start", "evaluation_period_end", "created_at", when_used="json")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        return to_utc_iso(dt)

