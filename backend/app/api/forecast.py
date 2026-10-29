from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.connection import get_db
from app.models.patient import Patient
from app.models.forecast import Forecast
from app.models.twin_state import TwinState
from app.models.user import User
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.forecasting.engine import ForecastingEngine
from app.services.auth import get_optional_current_user, verify_patient_authorization

router = APIRouter(prefix="/patients/{patient_id}", tags=["Forecasting"])


@router.post("/forecast", response_model=ForecastResponse)
def generate_forecast(
    patient_id: str,
    payload: ForecastRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a forward-looking physiological forecast rooted in the active digital twin state.
    Records model version, uncertainty bands, and explicit association to the active twin state version.
    """
    verify_patient_authorization(patient_id, current_user, db)

    try:
        record = ForecastingEngine.generate_forecast(
            patient_id=patient_id,
            db=db,
            horizon_minutes=payload.horizon_minutes or 120,
            model_type=payload.model_type or "autoregressive_trend"
        )
        return record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/forecasts", response_model=List[ForecastResponse])
def get_forecasts(
    patient_id: str,
    include_stale: bool = Query(True, description="Whether to include stale historical forecasts"),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all generated forecasts for a patient.
    Highlights whether each forecast is fresh or stale relative to current twin state.
    """
    verify_patient_authorization(patient_id, current_user, db)

    active_state = db.query(TwinState).filter(
        TwinState.patient_id == patient_id,
        TwinState.is_active_version == True
    ).first()

    query = db.query(Forecast).filter(Forecast.patient_id == patient_id)
    if not include_stale:
        query = query.filter(Forecast.is_stale == False)

    forecasts = query.order_by(Forecast.created_at.desc()).limit(limit).all()

    # Dynamic check: if state evolved beyond forecast's version, ensure flagged stale
    if active_state:
        for f in forecasts:
            if f.twin_state_version < active_state.state_version and not f.is_stale:
                f.is_stale = True
                f.stale_reason = f"State advanced to Version {active_state.state_version}."

    return forecasts

