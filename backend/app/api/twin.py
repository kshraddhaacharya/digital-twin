from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.connection import get_db
from app.models.patient import Patient
from app.models.twin_state import TwinState
from app.models.user import User
from app.schemas.twin import TwinStateResponse
from app.digital_twin.engine import DigitalTwinEngine
from app.services.auth import get_optional_current_user, verify_patient_authorization

router = APIRouter(prefix="/patients/{patient_id}/twin", tags=["Digital Twin"])


@router.get("", response_model=TwinStateResponse)
def get_current_twin_state(
    patient_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the active, current modeled physiological state for the patient's digital twin."""
    verify_patient_authorization(patient_id, current_user, db)

    state = DigitalTwinEngine.get_active_twin_state(patient_id=patient_id, db=db)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital twin has not been initialized for patient '{patient_id}'. Please upload measurements or call initialize."
        )

    return state


@router.get("/history", response_model=List[TwinStateResponse])
def get_twin_state_history(
    patient_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the complete historical audit log of all twin state versions."""
    verify_patient_authorization(patient_id, current_user, db)

    states = db.query(TwinState).filter(
        TwinState.patient_id == patient_id
    ).order_by(TwinState.state_version.desc()).all()

    return states


@router.post("/initialize", response_model=TwinStateResponse)
def initialize_twin(
    patient_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Initializes or resets the digital twin from stored observations (Version 1)."""
    verify_patient_authorization(patient_id, current_user, db)

    try:
        state = DigitalTwinEngine.initialize_twin(patient_id=patient_id, db=db)
        return state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

