from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database.connection import get_db
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientResponse, SyntheticPatientRequest
from app.data.synthetic import generate_synthetic_patient_data
from app.digital_twin.engine import DigitalTwinEngine
from app.services.ingestion import parse_iso_datetime
from app.services.clinical_metrics import calculate_bmi
from app.services.auth import get_optional_current_user, verify_patient_authorization
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/patients", tags=["Patients"])


def _to_patient_response(p: Patient) -> dict:
    bmi_val, bmi_cat = calculate_bmi(p.height_cm, p.weight_kg)
    return {
        "id": p.id,
        "name": p.name,
        "age": p.age,
        "gender": p.gender,
        "baseline_heart_rate": p.baseline_heart_rate,
        "height_cm": p.height_cm,
        "weight_kg": p.weight_kg,
        "profile_version": getattr(p, "profile_version", 1),
        "calculated_bmi": bmi_val,
        "bmi_category": bmi_cat,
        "medical_notes": p.medical_notes,
        "is_synthetic": p.is_synthetic,
        "created_at": to_utc_iso(p.created_at)
    }


@router.get("", response_model=List[PatientResponse])
def list_patients(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists patients:
    - If user is authenticated, returns their patient record plus available demo patients.
    - If unauthenticated, returns only synthetic demonstration patients.
    """
    query = db.query(Patient)
    if current_user:
        query = query.filter((Patient.id == current_user.patient_id) | (Patient.is_synthetic == True))
    else:
        query = query.filter(Patient.is_synthetic == True)

    patients = query.order_by(Patient.created_at.desc()).all()
    return [_to_patient_response(p) for p in patients]


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    """Registers a new patient with canonical physical metrics."""
    existing = db.query(Patient).filter(Patient.id == payload.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Patient with ID '{payload.id}' already exists."
        )

    patient = Patient(
        id=payload.id,
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        baseline_heart_rate=payload.baseline_heart_rate,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        profile_version=1,
        medical_notes=payload.medical_notes,
        is_synthetic=payload.is_synthetic,
        created_at=datetime.now(timezone.utc)
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return _to_patient_response(patient)


@router.post("/synthetic", status_code=status.HTTP_201_CREATED)
def create_or_load_synthetic_patient(payload: SyntheticPatientRequest, db: Session = Depends(get_db)):
    """
    Generates a deterministic synthetic patient telemetry stream, stores measurements,
    and initializes the Patient Digital Twin at Version 1.
    Strictly prevents overwriting real registered patient records.
    """
    pid = payload.patient_id or "PT-DEMO-001"

    existing = db.query(Patient).filter(Patient.id == pid).first()
    if existing:
        if not existing.is_synthetic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Safety violation: Patient ID '{pid}' belongs to a registered real user and cannot be overwritten with synthetic demo data."
            )
        db.delete(existing)
        db.commit()

    synthetic_bundle = generate_synthetic_patient_data(
        patient_id=pid,
        name=payload.name or "Alice M. Taylor",
        age=payload.age or 56,
        gender=payload.gender or "Female",
        baseline_hr=payload.baseline_hr or 72.0,
        duration_hours=payload.duration_hours or 24,
        interval_minutes=payload.interval_minutes or 15,
        noise_level=payload.noise_level or 1.2,
        include_exercise=payload.include_exercise_transient if payload.include_exercise_transient is not None else True
    )

    pt_info = synthetic_bundle["patient"]
    new_patient = Patient(
        id=pt_info["id"],
        name=pt_info["name"],
        age=pt_info["age"],
        gender=pt_info["gender"],
        baseline_heart_rate=pt_info["baseline_heart_rate"],
        height_cm=payload.height_cm or 165.0,
        weight_kg=payload.weight_kg or 68.0,
        profile_version=1,
        medical_notes=pt_info["medical_notes"],
        is_synthetic=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_patient)
    db.flush()

    # Insert synthetic measurements
    measurement_objs = []
    for m in synthetic_bundle["measurements"]:
        ts = parse_iso_datetime(m["timestamp"])
        measurement_objs.append(Measurement(
            patient_id=pid,
            timestamp=ts,
            measurement_type=m["measurement_type"],
            value=m["value"],
            unit=m["unit"],
            source=m["source"],
            context="resting" if m.get("value", 72) < 95 else "active",
            data_quality="valid",
            is_late_arrival=False
        ))
    db.add_all(measurement_objs)
    db.commit()

    # Initialize Digital Twin at State Version 1
    twin_state = DigitalTwinEngine.initialize_twin(patient_id=pid, db=db)

    bmi_val, bmi_cat = calculate_bmi(new_patient.height_cm, new_patient.weight_kg)

    return {
        "success": True,
        "patient": {
            "id": new_patient.id,
            "name": new_patient.name,
            "age": new_patient.age,
            "gender": new_patient.gender,
            "baseline_heart_rate": new_patient.baseline_heart_rate,
            "height_cm": new_patient.height_cm,
            "weight_kg": new_patient.weight_kg,
            "calculated_bmi": bmi_val,
            "bmi_category": bmi_cat,
            "is_synthetic": True
        },
        "measurements_loaded": len(measurement_objs),
        "twin_state_version": twin_state.state_version,
        "latest_heart_rate": twin_state.latest_heart_rate,
        "observation_window": synthetic_bundle["summary"]
    }


@router.get("/{patient_id}")
def get_patient(
    patient_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves patient details along with digital twin status with authorization checks."""
    patient = verify_patient_authorization(patient_id, current_user, db)

    active_twin = DigitalTwinEngine.get_active_twin_state(patient_id=patient_id, db=db)
    total_measurements = db.query(Measurement).filter(Measurement.patient_id == patient_id).count()
    bmi_val, bmi_cat = calculate_bmi(patient.height_cm, patient.weight_kg)

    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "baseline_heart_rate": patient.baseline_heart_rate,
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "profile_version": getattr(patient, "profile_version", 1),
        "calculated_bmi": bmi_val,
        "bmi_category": bmi_cat,
        "medical_notes": patient.medical_notes,
        "is_synthetic": patient.is_synthetic,
        "created_at": patient.created_at,
        "total_measurements": total_measurements,
        "active_twin_state_version": active_twin.state_version if active_twin else None,
        "latest_heart_rate": active_twin.latest_heart_rate if active_twin else None,
        "measurement_context": active_twin.measurement_context if active_twin else "resting",
        "latest_observation_time": active_twin.timestamp_latest_observation if active_twin else None,
        "vital_status": active_twin.vital_status if active_twin else "uninitialized",
        "data_quality_status": active_twin.data_quality_status if active_twin else "uninitialized",
        "attestation_status": active_twin.attestation_status if active_twin else "UNAVAILABLE",
        "on_chain_tx_hash": active_twin.on_chain_tx_hash if active_twin else None
    }

