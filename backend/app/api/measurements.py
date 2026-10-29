from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database.connection import get_db
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.models.twin_state import TwinState
from app.models.user import User
from app.schemas.measurement import MeasurementCreate, MeasurementResponse, MeasurementBatchUploadResponse
from app.digital_twin.engine import DigitalTwinEngine
from app.services.ingestion import process_csv_upload, process_json_upload, process_pdf_report
from app.services.auth import get_optional_current_user, verify_patient_authorization
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/patients/{patient_id}", tags=["Measurements"])


@router.get("/measurements", response_model=List[MeasurementResponse])
def get_measurements(
    patient_id: str,
    measurement_type: Optional[str] = Query(None, description="Filter by type, e.g. 'heart_rate'"),
    limit: int = Query(200, ge=1, le=1000, description="Max observations to return"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Fetches chronological measurements for a patient with authorization checks."""
    verify_patient_authorization(patient_id, current_user, db)

    query = db.query(Measurement).filter(Measurement.patient_id == patient_id)
    if measurement_type:
        query = query.filter(Measurement.measurement_type == measurement_type.lower())

    return query.order_by(Measurement.timestamp.desc()).limit(limit).all()


@router.post("/measurements", status_code=status.HTTP_201_CREATED)
def add_measurement(
    patient_id: str,
    payload: MeasurementCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a single timestamped measurement.
    Validates types, bounds, and context; prevents duplicates; saves transactionally;
    and advances the Digital Twin state version, invalidating stale forecasts.
    """
    verify_patient_authorization(patient_id, current_user, db)

    # 1. Duplicate check: unique (patient_id, measurement_type, timestamp)
    meas_ts = payload.timestamp
    if meas_ts.tzinfo is None:
        meas_ts = meas_ts.replace(tzinfo=timezone.utc)
    else:
        meas_ts = meas_ts.astimezone(timezone.utc)

    duplicate = db.query(Measurement).filter(
        Measurement.patient_id == patient_id,
        Measurement.measurement_type == payload.measurement_type,
        Measurement.timestamp == meas_ts
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate observation: An observation of type '{payload.measurement_type}' at timestamp '{meas_ts.isoformat()}' already exists."
        )

    # 2. Check for late arrival
    latest_existing = db.query(Measurement.timestamp).filter(
        Measurement.patient_id == patient_id,
        Measurement.measurement_type == payload.measurement_type
    ).order_by(Measurement.timestamp.desc()).first()

    is_late = False
    if latest_existing:
        latest_ts = latest_existing[0].replace(tzinfo=timezone.utc) if latest_existing[0].tzinfo is None else latest_existing[0]
        if meas_ts < latest_ts:
            is_late = True

    # 3. Store valid measurement
    new_m = Measurement(
        patient_id=patient_id,
        timestamp=meas_ts,
        measurement_type=payload.measurement_type,
        value=payload.value,
        unit=payload.unit,
        source=payload.source or "manual_entry",
        context=payload.context or "resting",
        data_quality="valid",
        is_late_arrival=is_late,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_m)
    db.commit()
    db.refresh(new_m)

    # 4. Trigger Digital Twin Engine state update
    active_state = db.query(TwinState).filter(
        TwinState.patient_id == patient_id,
        TwinState.is_active_version == True
    ).first()

    if not active_state:
        updated_state = DigitalTwinEngine.initialize_twin(patient_id=patient_id, db=db)
        stale_count = 0
    else:
        updated_state, stale_count = DigitalTwinEngine.update_twin_with_measurement(
            patient_id=patient_id,
            measurement=new_m,
            db=db
        )

    return {
        "success": True,
        "message": f"Measurement recorded successfully. Digital twin evolved to State Version {updated_state.state_version}.",
        "measurement": {
            "id": new_m.id,
            "patient_id": new_m.patient_id,
            "timestamp": to_utc_iso(new_m.timestamp),
            "measurement_type": new_m.measurement_type,
            "value": new_m.value,
            "unit": new_m.unit,
            "source": new_m.source,
            "context": new_m.context,
            "is_late_arrival": new_m.is_late_arrival,
            "created_at": to_utc_iso(new_m.created_at)
        },
        "digital_twin_update": {
            "previous_version": (updated_state.state_version - 1) if updated_state.state_version > 1 else 1,
            "current_state_version": updated_state.state_version,
            "latest_heart_rate": updated_state.latest_heart_rate,
            "measurement_context": updated_state.measurement_context,
            "rolling_mean_60m": updated_state.rolling_mean_60m,
            "trend_slope_per_hour": updated_state.trend_slope_per_hour,
            "vital_status": updated_state.vital_status,
            "data_quality_status": updated_state.data_quality_status,
            "attestation_status": updated_state.attestation_status,
            "on_chain_tx_hash": updated_state.on_chain_tx_hash,
            "stale_forecasts_invalidated": stale_count
        }
    }


@router.post("/upload-csv", response_model=MeasurementBatchUploadResponse)
async def upload_csv_measurements(
    patient_id: str,
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Uploads batch measurements from a CSV file with authorization checks."""
    verify_patient_authorization(patient_id, current_user, db)

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a .csv extension.")

    content = await file.read()
    result = process_csv_upload(file_bytes=content, patient_id=patient_id, db=db)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.get("error"))

    twin_ver = None
    if result["valid_inserted"] > 0:
        state = DigitalTwinEngine.initialize_twin(patient_id=patient_id, db=db)
        twin_ver = state.state_version

    return MeasurementBatchUploadResponse(
        success=True,
        patient_id=patient_id,
        total_processed=result["total_processed"],
        valid_inserted=result["valid_inserted"],
        duplicates_skipped=result["duplicates_skipped"],
        errors=result["errors"],
        twin_state_version=twin_ver
    )


@router.post("/upload-json", response_model=MeasurementBatchUploadResponse)
def upload_json_measurements(
    patient_id: str,
    payload: dict,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Uploads batch measurements from a JSON payload with authorization checks."""
    verify_patient_authorization(patient_id, current_user, db)

    result = process_json_upload(payload=payload, patient_id=patient_id, db=db)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.get("error"))

    twin_ver = None
    if result["valid_inserted"] > 0:
        state = DigitalTwinEngine.initialize_twin(patient_id=patient_id, db=db)
        twin_ver = state.state_version

    return MeasurementBatchUploadResponse(
        success=True,
        patient_id=patient_id,
        total_processed=result["total_processed"],
        valid_inserted=result["valid_inserted"],
        duplicates_skipped=result["duplicates_skipped"],
        errors=result["errors"],
        twin_state_version=twin_ver
    )


@router.post("/upload-pdf", response_model=MeasurementBatchUploadResponse)
async def upload_pdf_measurements(
    patient_id: str,
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Extracts timestamped telemetry measurements from a clinical PDF report with authorization checks."""
    verify_patient_authorization(patient_id, current_user, db)

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a .pdf extension.")

    content = await file.read()
    result = process_pdf_report(pdf_bytes=content, patient_id=patient_id, db=db)
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.get("error"))

    twin_ver = None
    if result["valid_inserted"] > 0:
        state = DigitalTwinEngine.initialize_twin(patient_id=patient_id, db=db)
        twin_ver = state.state_version

    return MeasurementBatchUploadResponse(
        success=True,
        patient_id=patient_id,
        total_processed=result["total_processed"],
        valid_inserted=result["valid_inserted"],
        duplicates_skipped=result["duplicates_skipped"],
        errors=result["errors"],
        twin_state_version=twin_ver
    )

