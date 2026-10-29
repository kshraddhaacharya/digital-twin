from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.patient import Patient
from app.schemas.evaluation import EvaluationResponse
from app.evaluation.engine import EvaluationEngine

router = APIRouter(prefix="/patients/{patient_id}", tags=["Model Evaluation"])


@router.get("/evaluation", response_model=EvaluationResponse)
def evaluate_models(
    patient_id: str,
    test_split_ratio: float = Query(0.20, ge=0.10, le=0.40, description="Held-out chronological test ratio"),
    db: Session = Depends(get_db)
):
    """
    Performs chronological train/test model evaluation on held-out observations.
    Evaluates MAE, RMSE, and compares against Baseline Persistence.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")

    try:
        results = EvaluationEngine.evaluate_models(
            patient_id=patient_id,
            db=db,
            test_split_ratio=test_split_ratio
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

