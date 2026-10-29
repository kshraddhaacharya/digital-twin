import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.models.twin_state import TwinState
from app.digital_twin.engine import DigitalTwinEngine
from app.schemas.auth import UserRegister, UserLogin, UserProfileUpdate, UserResponse, TokenResponse
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.services.clinical_metrics import calculate_bmi
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/auth", tags=["Authentication & User Accounts"])


def _to_user_response(user: User) -> dict:
    bmi_val, bmi_cat = calculate_bmi(user.height, user.body_weight)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "patient_id": user.patient_id,
        "age": user.age,
        "date_of_birth": user.date_of_birth,
        "gender": user.gender or "Prefer not to say",
        "height": user.height,
        "body_weight": user.body_weight,
        "profile_version": getattr(user, "profile_version", 1),
        "calculated_bmi": bmi_val,
        "bmi_category": bmi_cat,
        "existing_conditions": user.existing_conditions,
        "allergies": user.allergies,
        "medications": user.medications,
        "emergency_contact": user.emergency_contact,
        "profile_photo": user.profile_photo,
        "health_notes": user.health_notes,
        "created_at": user.created_at or datetime.now(timezone.utc)
    }


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    """Registers a new user and creates their personal Digital Twin entity."""
    existing_user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead."
        )

    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    patient_id = f"PT-{uuid.uuid4().hex[:8].upper()}"

    # Create associated Patient Digital Twin
    patient = Patient(
        id=patient_id,
        name=payload.full_name.strip(),
        age=payload.age if payload.age is not None else 45,
        gender=payload.gender.strip() if payload.gender else "Prefer not to say",
        baseline_heart_rate=72.0,
        height_cm=payload.height,
        weight_kg=payload.body_weight,
        profile_version=1,
        medical_notes=payload.existing_conditions or "Self-registered patient account.",
        is_synthetic=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(patient)
    db.flush()

    # Create User record with hashed password
    hashed_pwd = hash_password(payload.password)
    user = User(
        id=user_id,
        email=payload.email.lower().strip(),
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        patient_id=patient_id,
        age=payload.age,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender or "Prefer not to say",
        height=payload.height,
        body_weight=payload.body_weight,
        profile_version=1,
        existing_conditions=payload.existing_conditions,
        allergies=payload.allergies,
        medications=payload.medications,
        emergency_contact=payload.emergency_contact,
        health_notes=payload.health_notes,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.flush()

    # Seed an initial baseline measurement to initialize twin
    init_meas = Measurement(
        patient_id=patient_id,
        timestamp=datetime.now(timezone.utc),
        measurement_type="heart_rate",
        value=72.0,
        unit="bpm",
        source="onboarding_baseline",
        context="resting",
        data_quality="valid",
        is_late_arrival=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(init_meas)
    db.commit()

    # Initialize Digital Twin at version 1 (with on-chain attestation)
    try:
        DigitalTwinEngine.initialize_twin(patient_id=patient_id, db=db)
    except Exception as e:
        print(f"[WARN] Twin initialization warning during registration: {e}")

    db.refresh(user)

    token = create_access_token(data={"sub": user.id, "email": user.email, "patient_id": user.patient_id})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(_to_user_response(user))
    )


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticates a user with email and password and returns a JWT token."""
    login_id = (payload.email or payload.username or "").lower().strip()
    if not login_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required for authentication."
        )
    user = db.query(User).filter(User.email == login_id, User.is_active == True).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.id, "email": user.email, "patient_id": user.patient_id})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(_to_user_response(user))
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's profile and health configuration."""
    return UserResponse.model_validate(_to_user_response(current_user))


@router.put("/profile", response_model=UserResponse)
def update_user_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the user's personal health profile.
    Maintains synchronization with the canonical Patient record and increments profile_version.
    Invalidates stale forecasts if physiological attributes (age, height, weight) change.
    """
    update_data = payload.model_dump(exclude_unset=True)

    physio_changed = False
    for field, val in update_data.items():
        if field in ["height", "body_weight", "age", "gender"] and getattr(current_user, field) != val:
            physio_changed = True
        setattr(current_user, field, val)

    current_user.profile_version = getattr(current_user, "profile_version", 1) + 1

    # Keep linked Patient record synchronized
    patient = db.query(Patient).filter(Patient.id == current_user.patient_id).first()
    if patient:
        if payload.full_name is not None:
            patient.name = payload.full_name.strip()
        if payload.age is not None:
            patient.age = payload.age
        if payload.gender is not None:
            patient.gender = payload.gender
        if payload.height is not None:
            patient.height_cm = payload.height
        if payload.body_weight is not None:
            patient.weight_kg = payload.body_weight
        patient.profile_version = getattr(patient, "profile_version", 1) + 1

    # If physiological attributes changed, mark active twin forecasts stale
    if physio_changed:
        active_state = db.query(TwinState).filter(
            TwinState.patient_id == current_user.patient_id,
            TwinState.is_active_version == True
        ).first()
        if active_state:
            DigitalTwinEngine.invalidate_stale_forecasts(
                patient_id=current_user.patient_id,
                current_state_version=active_state.state_version + 1,
                db=db
            )

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(_to_user_response(current_user))


@router.delete("/account")
def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently deletes the user account and associated personal health records."""
    patient_id = current_user.patient_id

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient:
        db.delete(patient)

    db.delete(current_user)
    db.commit()

    return {
        "success": True,
        "message": "Your account and all associated personal health data have been permanently deleted."
    }

