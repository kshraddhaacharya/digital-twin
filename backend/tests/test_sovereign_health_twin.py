import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.main import app
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.models.twin_state import TwinState
from app.models.forecast import Forecast
from app.models.user import User
from app.models.report import MedicalReport
from app.digital_twin.engine import DigitalTwinEngine
from app.forecasting.engine import ForecastingEngine
from app.simulation.engine import SimulationEngine
from app.services.clinical_metrics import calculate_bmi, classify_vital_status
from app.web3.service import Web3Service
from app.services.auth import create_access_token, hash_password


# Isolated in-memory SQLite database for test suite
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# 1. Deterministic Output & Canonical Serialization
# =========================================================================
def test_deterministic_canonical_serialization():
    ts = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
    features_a = {
        "latest_heart_rate": 72.5,
        "rolling_mean_60m": 72.0,
        "trend_slope_per_hour": 0.25,
        "vital_status": "normal",
        "measurement_context": "resting",
    }
    features_b = {
        "trend_slope_per_hour": 0.25,
        "vital_status": "normal",
        "latest_heart_rate": 72.5,
        "measurement_context": "resting",
        "rolling_mean_60m": 72.0,
    }

    dict_a = Web3Service.canonicalize_state_payload(
        patient_id="PT-001",
        version=2,
        timestamp=ts,
        features=features_a,
    )
    dict_b = Web3Service.canonicalize_state_payload(
        patient_id="PT-001",
        version=2,
        timestamp=ts,
        features=features_b,
    )
    assert dict_a == dict_b, "Canonical dictionary representation must be deterministic"

    hash_a = Web3Service.calculate_state_hash(
        patient_id="PT-001",
        version=2,
        timestamp=ts,
        features=features_a,
    )
    hash_b = Web3Service.calculate_state_hash(
        patient_id="PT-001",
        version=2,
        timestamp=ts,
        features=features_b,
    )
    assert hash_a == hash_b
    assert len(hash_a) == 64, "SHA-256 hash must be 64 hexadecimal characters"


# =========================================================================
# 2. Insufficient Data Handling
# =========================================================================
def test_insufficient_data_handling(db_session):
    pt = Patient(
        id="PT-INSUF",
        name="Insufficient Data Patient",
        age=45,
        gender="Male",
        baseline_heart_rate=70.0,
        is_synthetic=True,
    )
    db_session.add(pt)
    db_session.commit()

    # Add only 3 observations (< 6 minimum required)
    now = datetime.now(timezone.utc)
    for i in range(3):
        m = Measurement(
            patient_id="PT-INSUF",
            timestamp=now - timedelta(minutes=(3 - i) * 15),
            measurement_type="heart_rate",
            value=72.0 + i,
            unit="bpm",
            source="manual",
            context="resting",
        )
        db_session.add(m)
    db_session.commit()

    # Twin initialization identifies insufficient_history
    twin_state = DigitalTwinEngine.initialize_twin("PT-INSUF", db_session)
    assert twin_state.data_quality_status == "insufficient_history"

    # Forecasting should refuse gracefully with a clear informative ValueError
    with pytest.raises(ValueError) as excinfo:
        ForecastingEngine.generate_forecast("PT-INSUF", db_session, horizon_minutes=120)
    assert "Insufficient historical data" in str(excinfo.value)


# =========================================================================
# 3. Irregular Intervals Handling & Quality Warnings
# =========================================================================
def test_irregular_intervals_handling(db_session):
    pt = Patient(
        id="PT-IRREG",
        name="Irregular Intervals Patient",
        age=50,
        gender="Female",
        baseline_heart_rate=68.0,
        is_synthetic=True,
    )
    db_session.add(pt)
    db_session.commit()

    now = datetime.now(timezone.utc)
    # 7 readings: first 5 spaced by 5 min, then huge gap of 180 min, then 1 reading
    timestamps = [
        now - timedelta(minutes=240),
        now - timedelta(minutes=235),
        now - timedelta(minutes=230),
        now - timedelta(minutes=225),
        now - timedelta(minutes=220),
        now - timedelta(minutes=15),
        now,
    ]
    for ts in timestamps:
        db_session.add(Measurement(
            patient_id="PT-IRREG",
            timestamp=ts,
            measurement_type="heart_rate",
            value=70.0,
            unit="bpm",
            source="manual",
        ))
    db_session.commit()

    twin_state = DigitalTwinEngine.initialize_twin("PT-IRREG", db_session)
    assert twin_state is not None

    forecast = ForecastingEngine.generate_forecast("PT-IRREG", db_session, horizon_minutes=120)
    assert forecast is not None
    assert any("Irregular observation intervals" in w for w in forecast.quality_warnings)


# =========================================================================
# 4. Outliers & Physiological Bounds
# =========================================================================
def test_outlier_and_bounds_validation(client, db_session):
    pt = Patient(
        id="PT-BOUNDS",
        name="Bounds Test Patient",
        age=30,
        gender="Other",
        baseline_heart_rate=72.0,
        is_synthetic=True,
    )
    db_session.add(pt)
    db_session.commit()

    # Rejection of impossible physiological values (< 30 or > 250 bpm)
    res_low = client.post("/api/patients/PT-BOUNDS/measurements", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurement_type": "heart_rate",
        "value": 15.0,  # Below 30 bpm
        "unit": "bpm",
        "source": "manual",
    })
    assert res_low.status_code in [400, 422]

    res_high = client.post("/api/patients/PT-BOUNDS/measurements", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurement_type": "heart_rate",
        "value": 310.0,  # Above 250 bpm
        "unit": "bpm",
        "source": "manual",
    })
    assert res_high.status_code in [400, 422]


# =========================================================================
# 5. Scenario Comparison (Scenario A vs Scenario B with Identical Start State)
# =========================================================================
def test_scenario_comparison_identical_start_and_kinetics(db_session):
    pt = Patient(
        id="PT-SCENARIO",
        name="Scenario Test Patient",
        age=40,
        gender="Female",
        baseline_heart_rate=75.0,
        is_synthetic=True,
    )
    db_session.add(pt)
    db_session.commit()

    now = datetime.now(timezone.utc)
    for i in range(12):
        db_session.add(Measurement(
            patient_id="PT-SCENARIO",
            timestamp=now - timedelta(minutes=(12 - i) * 15),
            measurement_type="heart_rate",
            value=74.0 + (i % 3),
            unit="bpm",
            source="sensor",
            context="resting",
        ))
    db_session.commit()
    DigitalTwinEngine.initialize_twin("PT-SCENARIO", db_session)

    res = SimulationEngine.run_simulation(
        patient_id="PT-SCENARIO",
        db=db_session,
        horizon_minutes=120,
        parameter_name="activity_exertion_factor",
        parameter_value=-25.0,  # Resting recovery
    )

    traj_a = res["scenario_a"]["simulated_trajectory"]
    traj_b = res["scenario_b"]["simulated_trajectory"]

    # Both scenarios must have identical horizon steps and identical start time
    assert len(traj_a) == len(traj_b)
    assert traj_a[0]["timestamp"] == traj_b[0]["timestamp"]

    # Trajectory B should reflect lower heart rate due to resting recovery
    endpoint_a = traj_a[-1]["simulated_value"]
    endpoint_b = traj_b[-1]["simulated_value"]
    assert endpoint_b < endpoint_a
    assert res["delta_summary"]["endpoint_delta_bpm"] > 0
    assert "disclaimer" in res


# =========================================================================
# 6. Stale Forecast Invalidation
# =========================================================================
def test_stale_forecast_invalidation(db_session):
    pt = Patient(
        id="PT-STALE",
        name="Stale Forecast Patient",
        age=35,
        gender="Male",
        baseline_heart_rate=70.0,
        profile_version=1,
        is_synthetic=True,
    )
    db_session.add(pt)
    db_session.commit()

    now = datetime.now(timezone.utc)
    for i in range(10):
        db_session.add(Measurement(
            patient_id="PT-STALE",
            timestamp=now - timedelta(minutes=(10 - i) * 15),
            measurement_type="heart_rate",
            value=70.0 + (i % 2),
            unit="bpm",
            source="sensor",
        ))
    db_session.commit()
    DigitalTwinEngine.initialize_twin("PT-STALE", db_session)

    # Generate initial forecast
    f1 = ForecastingEngine.generate_forecast("PT-STALE", db_session, horizon_minutes=120)
    assert f1.is_stale == False
    assert f1.twin_state_version == 1

    # Ingest a new measurement - twin updates to version 2
    new_m = Measurement(
        patient_id="PT-STALE",
        timestamp=now + timedelta(minutes=5),
        measurement_type="heart_rate",
        value=78.0,
        unit="bpm",
        source="sensor",
        context="resting",
    )
    db_session.add(new_m)
    db_session.commit()

    DigitalTwinEngine.update_twin_with_measurement("PT-STALE", new_m, db_session)

    db_session.refresh(f1)
    assert f1.is_stale == True
    assert "Twin state evolved to Version 2" in f1.stale_reason


# =========================================================================
# 7. Cross-Patient Access Control & Authorization
# =========================================================================
def test_cross_patient_authorization_isolation(client, db_session):
    # Register Patient A User
    user_a = User(
        id="USR-A",
        email="patient_a@health.org",
        hashed_password=hash_password("Password123!"),
        full_name="Patient Alpha",
        patient_id="PT-ALPHA",
    )
    patient_a = Patient(id="PT-ALPHA", name="Patient Alpha", age=30, gender="Female", baseline_heart_rate=70.0, is_synthetic=False)

    # Register Patient B
    user_b = User(
        id="USR-B",
        email="patient_b@health.org",
        hashed_password=hash_password("Password123!"),
        full_name="Patient Beta",
        patient_id="PT-BETA",
    )
    patient_b = Patient(id="PT-BETA", name="Patient Beta", age=32, gender="Male", baseline_heart_rate=72.0, is_synthetic=False)

    db_session.add_all([user_a, patient_a, user_b, patient_b])
    db_session.commit()

    token_a = create_access_token({"sub": "USR-A", "email": "patient_a@health.org"})

    # Patient A attempts to read Patient B's digital twin state -> Must be 403 Forbidden
    res = client.get(
        "/api/patients/PT-BETA/twin",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

    # Patient A attempts to post measurement to Patient B -> 403 Forbidden
    res_post = client.post(
        "/api/patients/PT-BETA/measurements",
        json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "measurement_type": "heart_rate",
            "value": 75.0,
            "unit": "bpm",
            "source": "manual"
        },
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_post.status_code == 403


# =========================================================================
# 8. Synthetic Patient Generator Cannot Overwrite Registered Real Patients
# =========================================================================
def test_synthetic_patient_cannot_overwrite_real_patient(client, db_session):
    real_patient = Patient(
        id="PT-REAL-999",
        name="Real Authenticated Person",
        age=55,
        gender="Female",
        baseline_heart_rate=68.0,
        is_synthetic=False,  # Protected!
    )
    db_session.add(real_patient)
    db_session.commit()

    res = client.post("/api/patients/synthetic", json={
        "patient_id": "PT-REAL-999",
        "name": "Overwriting Attempt",
        "baseline_hr": 80.0,
        "duration_hours": 24
    })
    assert res.status_code == 400
    assert "cannot be overwritten with synthetic demo data" in res.json()["detail"]


# =========================================================================
# 9. Magic-Bytes File Validation & Biomarker Confirmation Workflow
# =========================================================================
def test_report_magic_bytes_validation_and_confirmation(client, db_session):
    user = User(
        id="USR-REP",
        email="report_tester@health.org",
        hashed_password=hash_password("Password123!"),
        full_name="Report Tester",
        patient_id="PT-REP",
    )
    patient = Patient(id="PT-REP", name="Report Tester", age=42, gender="Female", baseline_heart_rate=72.0)
    db_session.add_all([user, patient])
    db_session.commit()

    token = create_access_token({"sub": "USR-REP", "email": "report_tester@health.org"})

    # 1. Reject fake PDF (file extension .pdf, but content is raw text/garbage without %PDF header)
    fake_pdf = b"Hello, this is just plain text disguised as a PDF file."
    res_fake = client.post(
        "/api/reports/upload",
        files={"file": ("malicious.pdf", fake_pdf, "application/pdf")},
        data={"title": "Fake PDF Test", "report_date": "2026-10-28"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_fake.status_code == 400
    assert "valid PDF header" in res_fake.json()["detail"]

    # 2. Accept valid PDF header
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res_valid = client.post(
        "/api/reports/upload",
        files={"file": ("lab_result.pdf", valid_pdf, "application/pdf")},
        data={"title": "Valid Lab Report", "report_date": "2026-10-28"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_valid.status_code in [200, 201]
    report_id = res_valid.json()["report"]["id"]

    # 3. Patient Review-and-Confirm biomarker workflow
    res_confirm = client.post(
        f"/api/reports/{report_id}/confirm-biomarkers",
        json={
            "key": "heart_rate",
            "value": 76.0,
            "unit": "bpm",
            "context": "resting"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["success"] == True
    assert "digital_twin_update" in res_confirm.json()
    assert res_confirm.json()["measurement"]["value"] == 76.0


# =========================================================================
# 10. Web3 Verification Status States (VERIFIED, MISMATCH, NOT_ANCHORED)
# =========================================================================
def test_web3_verification_status_distinctions():
    web3_svc = Web3Service.get_instance()
    ts = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
    features = {
        "latest_heart_rate": 72.0,
        "rolling_mean_60m": 72.0,
        "trend_slope_per_hour": 0.0,
        "vital_status": "normal",
        "measurement_context": "resting",
    }

    # 1. Attest state
    res_attest = web3_svc.attest_twin_state(
        patient_id="PT-VERIFY",
        version=1,
        timestamp=ts,
        latest_hr=72.0,
        rolling_mean=72.0,
        features=features,
    )
    assert res_attest["attestation_status"] in ["VERIFIED", "SIMULATED", "UNAVAILABLE"]

    if res_attest["attestation_status"] in ["VERIFIED", "SIMULATED"]:
        # 2. Verify with matching state features
        res_match = web3_svc.verify_twin_attestation(
            patient_id="PT-VERIFY",
            version=1,
            timestamp=ts,
            features=features,
        )
        assert res_match["verification_status"] == "VERIFIED"
        assert res_match["is_valid"] == True

        # 3. Verify with tampered state features (MISMATCH)
        tampered_features = dict(features)
        tampered_features["latest_heart_rate"] = 135.0  # Secretly altered!
        res_mismatch = web3_svc.verify_twin_attestation(
            patient_id="PT-VERIFY",
            version=1,
            timestamp=ts,
            features=tampered_features,
        )
        assert res_mismatch["verification_status"] == "MISMATCH"
        assert res_mismatch["is_valid"] == False

        # 4. Verify unanchored version (NOT_ANCHORED)
        res_unanchored = web3_svc.verify_twin_attestation(
            patient_id="PT-VERIFY",
            version=99,  # Never anchored
            timestamp=ts,
            features=features,
        )
        assert res_unanchored["verification_status"] == "NOT_ANCHORED"


# =========================================================================
# 11. Clinical Metrics: BMI Calculation & Non-Diagnostic Classification
# =========================================================================
def test_clinical_bmi_screening_and_classification():
    # 165 cm, 68 kg -> 68 / (1.65)^2 = 24.98 kg/m^2 -> 25.0 kg/m^2
    bmi, category = calculate_bmi(165.0, 68.0)
    assert bmi == 25.0
    assert "screening range" in category

    # Missing values return None gracefully
    bmi_none, cat_none = calculate_bmi(None, 68.0)
    assert bmi_none is None
    assert cat_none is None

    # Context-aware vital status classification
    # 105 bpm during mild activity is expected physiological dynamics (< 120 bpm)
    stat_active = classify_vital_status(105.0, context="active")
    assert stat_active["status"] == "active_moderate"
    assert stat_active["requires_urgent_care"] == False

    # 115 bpm at rest is classified as resting tachycardia
    stat_resting = classify_vital_status(115.0, context="resting")
    assert stat_resting["status"] == "tachycardia"
    assert "Elevated Resting Rate" in stat_resting["label"]

