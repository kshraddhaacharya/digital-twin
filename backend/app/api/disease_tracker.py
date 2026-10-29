from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.disease_tracker import HealthCondition, ConditionLog
from app.models.twin_state import TwinState
from app.services.auth import get_current_user
from app.services.clinical_metrics import calculate_bmi
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/disease-tracker", tags=["Disease Tracker & Health Timeline"])


# Schemas
class ConditionCreate(BaseModel):
    condition_name: str = Field(..., min_length=1, max_length=128)
    diagnosed_date: Optional[str] = None
    severity: str = Field("monitoring", description="'mild', 'moderate', 'severe', or 'monitoring'")
    status: str = Field("active", description="'active', 'managed', or 'resolved'")
    notes: Optional[str] = None


class LogCreate(BaseModel):
    condition_id: Optional[int] = None
    log_date: str = Field(..., description="Date/timestamp of measurement, e.g., '2026-10-25'")
    metric_name: str = Field(..., description="e.g. 'Systolic BP', 'Resting Heart Rate', 'Blood Glucose'")
    metric_value: float
    metric_unit: str = Field(..., description="e.g. 'mmHg', 'bpm', 'mg/dL'")
    symptoms: Optional[str] = None
    notes: Optional[str] = None


# Endpoints for Conditions
@router.post("/conditions", status_code=status.HTTP_201_CREATED)
def create_condition(
    payload: ConditionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a health condition to monitor."""
    condition = HealthCondition(
        user_id=current_user.id,
        patient_id=current_user.patient_id,
        condition_name=payload.condition_name.strip(),
        diagnosed_date=payload.diagnosed_date.strip() if payload.diagnosed_date else None,
        severity=payload.severity,
        status=payload.status,
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(condition)
    db.commit()
    db.refresh(condition)
    return {
        "id": condition.id,
        "condition_name": condition.condition_name,
        "diagnosed_date": condition.diagnosed_date,
        "severity": condition.severity,
        "status": condition.status,
        "notes": condition.notes,
        "created_at": to_utc_iso(condition.created_at)
    }


@router.get("/conditions")
def list_conditions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all health conditions being monitored by the user."""
    conditions = db.query(HealthCondition).filter(
        HealthCondition.user_id == current_user.id
    ).order_by(HealthCondition.created_at.desc()).all()

    return [
        {
            "id": c.id,
            "condition_name": c.condition_name,
            "diagnosed_date": c.diagnosed_date,
            "severity": c.severity,
            "status": c.status,
            "notes": c.notes,
            "total_logs": len(c.logs),
            "created_at": to_utc_iso(c.created_at)
        }
        for c in conditions
    ]


@router.delete("/conditions/{condition_id}")
def delete_condition(
    condition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a tracked health condition and its historical entries."""
    cond = db.query(HealthCondition).filter(
        HealthCondition.id == condition_id,
        HealthCondition.user_id == current_user.id
    ).first()
    if not cond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found.")

    db.delete(cond)
    db.commit()
    return {"success": True, "message": "Condition deleted successfully."}


# Endpoints for Timeline Logs
@router.post("/logs", status_code=status.HTTP_201_CREATED)
def create_condition_log(
    payload: LogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a measurement, symptom, or note entry to the health timeline."""
    log_entry = ConditionLog(
        condition_id=payload.condition_id,
        user_id=current_user.id,
        patient_id=current_user.patient_id,
        log_date=payload.log_date.strip(),
        metric_name=payload.metric_name.strip(),
        metric_value=payload.metric_value,
        metric_unit=payload.metric_unit.strip(),
        symptoms=payload.symptoms.strip() if payload.symptoms else None,
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return {
        "id": log_entry.id,
        "condition_id": log_entry.condition_id,
        "log_date": log_entry.log_date,
        "metric_name": log_entry.metric_name,
        "metric_value": log_entry.metric_value,
        "metric_unit": log_entry.metric_unit,
        "symptoms": log_entry.symptoms,
        "notes": log_entry.notes,
        "created_at": to_utc_iso(log_entry.created_at)
    }


@router.get("/logs")
def list_condition_logs(
    condition_id: Optional[int] = Query(None),
    metric_name: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns chronological health logs for the user."""
    query = db.query(ConditionLog).filter(ConditionLog.user_id == current_user.id)
    if condition_id:
        query = query.filter(ConditionLog.condition_id == condition_id)
    if metric_name:
        query = query.filter(ConditionLog.metric_name == metric_name)

    logs = query.order_by(ConditionLog.log_date.asc(), ConditionLog.created_at.asc()).all()
    return [
        {
            "id": l.id,
            "condition_id": l.condition_id,
            "condition_name": l.condition.condition_name if l.condition else "General",
            "log_date": l.log_date,
            "metric_name": l.metric_name,
            "metric_value": l.metric_value,
            "metric_unit": l.metric_unit,
            "symptoms": l.symptoms,
            "notes": l.notes,
            "created_at": to_utc_iso(l.created_at)
        }
        for l in logs
    ]


@router.delete("/logs/{log_id}")
def delete_condition_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a health timeline log entry."""
    entry = db.query(ConditionLog).filter(
        ConditionLog.id == log_id,
        ConditionLog.user_id == current_user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found.")

    db.delete(entry)
    db.commit()
    return {"success": True, "message": "Log entry deleted."}


@router.get("/analytics")
def get_disease_tracker_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes summary health analytics, disease risk indicators, and
    correlations using Digital Twin state and condition logs.
    """
    twin = db.query(TwinState).filter(
        TwinState.patient_id == current_user.patient_id,
        TwinState.is_active_version == True
    ).first()

    latest_hr = twin.latest_heart_rate if twin else (current_user.age or 72.0)
    rolling_std = twin.rolling_std_60m if twin else 2.0
    slope = twin.trend_slope_per_hour if twin else 0.0

    # Cardiovascular risk category based on physiological indicators
    if latest_hr > 100:
        cv_status = "Tachycardia Alert (> 100 bpm)"
        cv_level = "High"
    elif latest_hr < 55:
        cv_status = "Bradycardia Caution (< 55 bpm)"
        cv_level = "Moderate"
    elif 60 <= latest_hr <= 85:
        cv_status = "Optimal Resting Dynamics"
        cv_level = "Low"
    else:
        cv_status = "Mild Elevation (85 - 100 bpm)"
        cv_level = "Moderate"

    # Autonomic Stress / Fatigue index
    stress_score = min(100, max(10, int((rolling_std * 8) + abs(slope * 4))))
    if stress_score < 35:
        stress_status = "Calm & Rested"
    elif stress_score < 70:
        stress_status = "Moderate Autonomic Activity"
    else:
        stress_status = "Elevated Physiological Strain"

    # BMI calculation via shared trusted clinical metrics module
    bmi, bmi_category = calculate_bmi(current_user.height, current_user.body_weight)

    conditions_count = db.query(HealthCondition).filter(HealthCondition.user_id == current_user.id).count()
    logs_count = db.query(ConditionLog).filter(ConditionLog.user_id == current_user.id).count()

    return {
        "cardiovascular": {
            "status": cv_status,
            "risk_level": cv_level,
            "latest_heart_rate_bpm": latest_hr,
            "trend_slope_bpm_per_hr": slope
        },
        "stress_fatigue": {
            "score_0_to_100": stress_score,
            "status": stress_status,
            "physiological_variability": rolling_std
        },
        "body_mass_index": {
            "bmi": bmi,
            "category": bmi_category,
            "height_cm": current_user.height,
            "body_weight_kg": current_user.body_weight
        },
        "tracking_summary": {
            "monitored_conditions_count": conditions_count,
            "total_timeline_logs": logs_count
        },
        "disclaimer": "Educational & research demonstration only. Not a medical diagnosis or clinical prescription."
    }

