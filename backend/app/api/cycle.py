from datetime import datetime, date, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.cycle import PeriodCycle
from app.models.twin_state import TwinState
from app.services.auth import get_current_user
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/cycle", tags=["Menstrual / Period Tracker"])


class CycleLogCreate(BaseModel):
    start_date: str = Field(..., description="Period start date, e.g., '2026-10-15'")
    end_date: Optional[str] = Field(None, description="Period end date, e.g., '2026-10-20'")
    cycle_length_days: int = Field(28, ge=20, le=45, description="Average cycle duration")
    period_length_days: int = Field(5, ge=2, le=10, description="Bleeding duration")
    flow_intensity: str = Field("medium", description="'light', 'medium', 'heavy', or 'spotting'")
    symptoms: Optional[str] = Field(None, description="Comma-separated or JSON list of symptoms")
    notes: Optional[str] = None


@router.post("/log", status_code=status.HTTP_201_CREATED)
def log_period_cycle(
    payload: CycleLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records a new menstrual period cycle log."""
    cycle = PeriodCycle(
        user_id=current_user.id,
        patient_id=current_user.patient_id,
        start_date=payload.start_date.strip(),
        end_date=payload.end_date.strip() if payload.end_date else None,
        cycle_length_days=payload.cycle_length_days,
        period_length_days=payload.period_length_days,
        flow_intensity=payload.flow_intensity,
        symptoms=payload.symptoms.strip() if payload.symptoms else None,
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return {
        "id": cycle.id,
        "start_date": cycle.start_date,
        "end_date": cycle.end_date,
        "cycle_length_days": cycle.cycle_length_days,
        "period_length_days": cycle.period_length_days,
        "flow_intensity": cycle.flow_intensity,
        "symptoms": cycle.symptoms,
        "notes": cycle.notes,
        "created_at": to_utc_iso(cycle.created_at)
    }


@router.get("/history")
def list_cycle_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists past menstrual cycle logs in reverse chronological order."""
    logs = db.query(PeriodCycle).filter(
        PeriodCycle.user_id == current_user.id
    ).order_by(PeriodCycle.start_date.desc()).all()

    return [
        {
            "id": l.id,
            "start_date": l.start_date,
            "end_date": l.end_date,
            "cycle_length_days": l.cycle_length_days,
            "period_length_days": l.period_length_days,
            "flow_intensity": l.flow_intensity,
            "symptoms": l.symptoms,
            "notes": l.notes,
            "created_at": to_utc_iso(l.created_at)
        }
        for l in logs
    ]


@router.delete("/{cycle_id}")
def delete_cycle_log(
    cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a cycle log entry."""
    entry = db.query(PeriodCycle).filter(
        PeriodCycle.id == cycle_id,
        PeriodCycle.user_id == current_user.id
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle record not found.")

    db.delete(entry)
    db.commit()
    return {"success": True, "message": "Cycle record deleted."}


@router.get("/summary")
def get_cycle_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes current cycle phase, predicted next period date, fertile window,
    and physiological digital twin heart rate correlation.
    """
    latest_cycle = db.query(PeriodCycle).filter(
        PeriodCycle.user_id == current_user.id
    ).order_by(PeriodCycle.start_date.desc()).first()

    today = date.today()

    if not latest_cycle:
        # Default placeholder when no cycle recorded yet
        return {
            "has_data": False,
            "message": "No cycle data logged yet. Please record your most recent period start date.",
            "average_cycle_length": 28,
            "phase": "Not Set",
            "current_day": None,
            "days_until_next_period": None
        }

    try:
        start_d = datetime.strptime(latest_cycle.start_date[:10], "%Y-%m-%d").date()
    except Exception:
        start_d = today

    cycle_len = latest_cycle.cycle_length_days or 28
    days_elapsed = (today - start_d).days
    current_day = (days_elapsed % cycle_len) + 1
    days_until_next = cycle_len - (days_elapsed % cycle_len)
    next_period_date = today + timedelta(days=days_until_next)

    # Determine biological cycle phase
    if current_day <= 5:
        phase = "Menstrual Phase"
        phase_desc = "Uterine lining shedding. Estrogen and progesterone are at baseline resting levels."
        hr_effect = "Resting heart rate is typically at its lowest monthly baseline."
    elif 6 <= current_day <= 13:
        phase = "Follicular Phase"
        phase_desc = "Follicles developing. Rising estrogen levels increase energy and physiological stamina."
        hr_effect = "Heart rate remains stable and resting rates are low."
    elif 14 <= current_day <= 16:
        phase = "Ovulation Window"
        phase_desc = "Luteinizing hormone surge triggers egg release. Peak fertile window."
        hr_effect = "Slight uptick in basal body temperature and resting heart rate (+1 to +2 bpm)."
    else:
        phase = "Luteal Phase"
        phase_desc = "Progesterone dominance preparing uterine lining. Metabolic rate increases."
        hr_effect = "Resting heart rate typically elevates by +2 to +5 bpm due to thermogenic progesterone."

    # Fertile window approximation (days 10 to 16)
    fertile_start = start_d + timedelta(days=9)
    fertile_end = start_d + timedelta(days=15)

    # Correlate with active twin state
    twin = db.query(TwinState).filter(
        TwinState.patient_id == current_user.patient_id,
        TwinState.is_active_version == True
    ).first()
    twin_hr = twin.latest_heart_rate if twin else 72.0

    return {
        "has_data": True,
        "last_period_start": latest_cycle.start_date,
        "cycle_length_days": cycle_len,
        "period_length_days": latest_cycle.period_length_days,
        "current_cycle_day": current_day,
        "current_phase": phase,
        "phase_description": phase_desc,
        "days_until_next_period": days_until_next,
        "predicted_next_period": next_period_date.isoformat(),
        "fertile_window": {
            "start": fertile_start.isoformat(),
            "end": fertile_end.isoformat(),
            "is_in_fertile_window": (10 <= current_day <= 16)
        },
        "physiological_correlation": {
            "current_twin_heart_rate_bpm": twin_hr,
            "expected_phase_shift": hr_effect
        }
    }

