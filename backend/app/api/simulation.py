from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.connection import get_db
from app.models.patient import Patient
from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.scenario import ScenarioSimulateRequest, ScenarioComparisonResponse, ScenarioResponse
from app.simulation.engine import SimulationEngine
from app.services.auth import get_optional_current_user, verify_patient_authorization

router = APIRouter(prefix="/patients/{patient_id}", tags=["Simulation"])


@router.post("/simulate", response_model=ScenarioComparisonResponse)
def simulate_scenarios(
    patient_id: str,
    payload: ScenarioSimulateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a counterfactual scenario simulation:
    - Scenario A: Baseline trajectory from active twin state
    - Scenario B: Hypothetical altered condition with transparent parameter adjustment and mathematical kinetics.
    """
    verify_patient_authorization(patient_id, current_user, db)

    try:
        result = SimulationEngine.run_simulation(
            patient_id=patient_id,
            db=db,
            horizon_minutes=payload.horizon_minutes or 120,
            parameter_name=payload.parameter_name or "activity_exertion_factor",
            parameter_value=payload.parameter_value,
            parameter_unit=payload.parameter_unit or "%"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/scenarios", response_model=List[ScenarioResponse])
def get_scenarios(
    patient_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves stored historical scenario records for a patient."""
    verify_patient_authorization(patient_id, current_user, db)

    return db.query(Scenario).filter(
        Scenario.patient_id == patient_id
    ).order_by(Scenario.created_at.desc()).limit(limit).all()

