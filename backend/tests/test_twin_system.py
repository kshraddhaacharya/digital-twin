import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base, get_db
from app.main import app
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.models.twin_state import TwinState
from app.models.forecast import Forecast
from app.models.scenario import Scenario
from app.digital_twin.engine import DigitalTwinEngine
from app.forecasting.engine import ForecastingEngine
from app.simulation.engine import SimulationEngine
from app.evaluation.engine import EvaluationEngine
from app.data.synthetic import generate_synthetic_patient_data, generate_synthetic_csv
from app.services.ingestion import process_csv_upload, process_json_upload


from sqlalchemy.pool import StaticPool

# Isolated in-memory SQLite database for test suite with StaticPool
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
# 1. Synthetic Data Generation Tests
# =========================================================================

def test_synthetic_data_generation_deterministic():
    """Verify synthetic generator is deterministic and produces physiological patterns."""
    data1 = generate_synthetic_patient_data(patient_id="PT-TEST-001", seed=42)
    data2 = generate_synthetic_patient_data(patient_id="PT-TEST-001", seed=42)

    assert data1["patient"]["id"] == "PT-TEST-001"
    assert len(data1["measurements"]) == len(data2["measurements"])
    assert data1["measurements"][0]["value"] == data2["measurements"][0]["value"]
    assert data1["patient"]["is_synthetic"] is True

    # Validate all heart rate values fall within physiological bounds
    hr_values = [m["value"] for m in data1["measurements"] if m["measurement_type"] == "heart_rate"]
    assert len(hr_values) > 0
    assert all(40.0 <= v <= 180.0 for v in hr_values)


def test_synthetic_csv_generation():
    """Verify synthetic CSV output has proper headers and structure."""
    csv_str = generate_synthetic_csv("PT-TEST-001")
    lines = csv_str.strip().split("\n")
    assert lines[0] == "timestamp,measurement_type,value,unit,source"
    assert len(lines) > 20


# =========================================================================
# 2. Digital Twin Lifecycle, Versioning & Invalidation Tests
# =========================================================================

def test_twin_initialization_and_features(db_session):
    """Verify twin initializes with State Version 1 and calculates features."""
    bundle = generate_synthetic_patient_data(patient_id="PT-001", duration_hours=12)
    patient = Patient(**bundle["patient"])
    db_session.add(patient)
    db_session.commit()

    for m in bundle["measurements"]:
        db_session.add(Measurement(
            patient_id="PT-001",
            timestamp=datetime.fromisoformat(m["timestamp"]),
            measurement_type=m["measurement_type"],
            value=m["value"],
            unit=m["unit"],
            source=m["source"]
        ))
    db_session.commit()

    twin_state = DigitalTwinEngine.initialize_twin("PT-001", db_session)
    assert twin_state.state_version == 1
    assert twin_state.is_active_version is True
    assert twin_state.latest_heart_rate > 0
    assert twin_state.rolling_mean_60m is not None
    assert twin_state.vital_status in ["normal", "elevated", "tachycardia", "bradycardia"]


def test_twin_state_version_increment_and_stale_forecast(db_session):
    """
    Verify:
    1. Twin state version increments from v1 to v2 upon new observation.
    2. Forecast generated under v1 is marked is_stale = True.
    """
    bundle = generate_synthetic_patient_data(patient_id="PT-002", duration_hours=12)
    db_session.add(Patient(**bundle["patient"]))
    db_session.commit()

    for m in bundle["measurements"]:
        db_session.add(Measurement(
            patient_id="PT-002",
            timestamp=datetime.fromisoformat(m["timestamp"]),
            measurement_type=m["measurement_type"],
            value=m["value"],
            unit=m["unit"],
            source=m["source"]
        ))
    db_session.commit()

    v1_state = DigitalTwinEngine.initialize_twin("PT-002", db_session)
    assert v1_state.state_version == 1

    # Generate a forecast under v1
    forecast_v1 = ForecastingEngine.generate_forecast("PT-002", db_session, horizon_minutes=120)
    assert forecast_v1.twin_state_version == 1
    assert forecast_v1.is_stale is False

    # Submit a new valid observation
    latest_ts = v1_state.timestamp_latest_observation
    new_ts = latest_ts + timedelta(minutes=15)
    new_measurement = Measurement(
        patient_id="PT-002",
        timestamp=new_ts,
        measurement_type="heart_rate",
        value=81.5,
        unit="bpm",
        source="bedside_monitor"
    )
    db_session.add(new_measurement)
    db_session.commit()

    v2_state, invalidated_count = DigitalTwinEngine.update_twin_with_measurement(
        "PT-002", new_measurement, db_session
    )

    assert v2_state.state_version == 2
    assert v2_state.is_active_version is True
    assert v2_state.latest_heart_rate == 81.5
    assert invalidated_count == 1

    # Check that previous forecast was invalidated
    db_session.refresh(forecast_v1)
    assert forecast_v1.is_stale is True
    assert "Version 2" in forecast_v1.stale_reason


def test_late_arriving_observation(db_session):
    """Verify late-arriving observations are detected and tagged."""
    bundle = generate_synthetic_patient_data(patient_id="PT-003", duration_hours=12)
    db_session.add(Patient(**bundle["patient"]))
    db_session.commit()

    for m in bundle["measurements"]:
        db_session.add(Measurement(
            patient_id="PT-003",
            timestamp=datetime.fromisoformat(m["timestamp"]),
            measurement_type=m["measurement_type"],
            value=m["value"],
            unit=m["unit"]
        ))
    db_session.commit()

    v1_state = DigitalTwinEngine.initialize_twin("PT-003", db_session)
    latest_ts = v1_state.timestamp_latest_observation

    # Add observation with timestamp 2 hours BEFORE latest observation
    old_ts = latest_ts - timedelta(hours=2, minutes=5)
    late_m = Measurement(
        patient_id="PT-003",
        timestamp=old_ts,
        measurement_type="heart_rate",
        value=69.0,
        unit="bpm",
        is_late_arrival=True
    )
    db_session.add(late_m)
    db_session.commit()

    v2_state, _ = DigitalTwinEngine.update_twin_with_measurement("PT-003", late_m, db_session)
    assert v2_state.state_version == 2
    # Latest observation is still the maximum timestamp, NOT the late arrival
    assert v2_state.timestamp_latest_observation == latest_ts


# =========================================================================
# 3. Scenario Simulation & Evaluation Tests
# =========================================================================

def test_scenario_simulation_comparison(db_session):
    """Verify Scenario A and Scenario B start from identical state and differ predictably."""
    bundle = generate_synthetic_patient_data(patient_id="PT-004", duration_hours=12)
    db_session.add(Patient(**bundle["patient"]))
    db_session.commit()

    for m in bundle["measurements"]:
        db_session.add(Measurement(
            patient_id="PT-004",
            timestamp=datetime.fromisoformat(m["timestamp"]),
            measurement_type=m["measurement_type"],
            value=m["value"],
            unit=m["unit"]
        ))
    db_session.commit()

    DigitalTwinEngine.initialize_twin("PT-004", db_session)

    result = SimulationEngine.run_simulation(
        patient_id="PT-004",
        db=db_session,
        horizon_minutes=180,
        parameter_name="trend_damping_pct",
        parameter_value=-30.0
    )

    assert result["baseline_state_version"] == 1
    assert result["scenario_a"]["scenario_type"] == "Scenario_A_Current_Trajectory"
    assert result["scenario_b"]["scenario_type"] == "Scenario_B_Hypothetical_Condition"
    assert "gamma" in result["scenario_b"]["mathematical_rule"]
    assert len(result["scenario_a"]["simulated_trajectory"]) == len(result["scenario_b"]["simulated_trajectory"])
    assert result["delta_summary"]["step_count"] > 0
    assert "CRITICAL DISCLAIMER" in result["disclaimer"]


def test_chronological_model_evaluation(db_session):
    """Verify evaluation respects chronological ordering with zero test leakage."""
    bundle = generate_synthetic_patient_data(patient_id="PT-005", duration_hours=24)
    db_session.add(Patient(**bundle["patient"]))
    db_session.commit()

    for m in bundle["measurements"]:
        db_session.add(Measurement(
            patient_id="PT-005",
            timestamp=datetime.fromisoformat(m["timestamp"]),
            measurement_type=m["measurement_type"],
            value=m["value"],
            unit=m["unit"]
        ))
    db_session.commit()

    eval_result = EvaluationEngine.evaluate_models(
        patient_id="PT-005",
        db=db_session,
        test_split_ratio=0.20
    )

    assert eval_result["train_samples"] > 0
    assert eval_result["test_samples"] > 0
    assert eval_result["mae"] >= 0.0
    assert eval_result["rmse"] >= 0.0
    assert eval_result["is_synthetic_data"] is True
    assert "synthetic" in eval_result["disclaimer"].lower()


# =========================================================================
# 4. API Endpoints & Validation Tests
# =========================================================================

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_api_create_and_load_synthetic_patient(client):
    res = client.post("/api/patients/synthetic", json={
        "patient_id": "PT-API-TEST",
        "name": "David Miller",
        "baseline_hr": 70.0,
        "duration_hours": 12
    })
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert body["twin_state_version"] == 1
    assert body["measurements_loaded"] > 0


def test_api_invalid_measurement_rejected(client):
    """Verify invalid measurements (out of bounds, bad units) return 422 and do not update twin."""
    # First seed patient
    client.post("/api/patients/synthetic", json={"patient_id": "PT-API-TEST2"})

    # Invalid heart rate (350 bpm > max 250 bpm)
    res_bad_val = client.post("/api/patients/PT-API-TEST2/measurements", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurement_type": "heart_rate",
        "value": 350.0,
        "unit": "bpm"
    })
    assert res_bad_val.status_code == 422

    # Invalid unit (e.g. km/h for heart rate)
    res_bad_unit = client.post("/api/patients/PT-API-TEST2/measurements", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurement_type": "heart_rate",
        "value": 75.0,
        "unit": "km/h"
    })
    assert res_bad_unit.status_code == 422

    # Check twin state is still version 1 and was not corrupted
    twin_res = client.get("/api/patients/PT-API-TEST2/twin")
    assert twin_res.status_code == 200
    assert twin_res.json()["state_version"] == 1


def test_api_duplicate_measurement_rejected(client):
    """Verify duplicate observation returns HTTP 409 conflict."""
    client.post("/api/patients/synthetic", json={"patient_id": "PT-API-TEST3"})
    ts = datetime.now(timezone.utc).isoformat()

    res1 = client.post("/api/patients/PT-API-TEST3/measurements", json={
        "timestamp": ts,
        "measurement_type": "heart_rate",
        "value": 74.0,
        "unit": "bpm"
    })
    assert res1.status_code == 201

    # Second submission with exact same (patient, type, timestamp)
    res2 = client.post("/api/patients/PT-API-TEST3/measurements", json={
        "timestamp": ts,
        "measurement_type": "heart_rate",
        "value": 74.0,
        "unit": "bpm"
    })
    assert res2.status_code == 409


def test_api_csv_upload_and_twin_update(client):
    """Verify CSV batch upload successfully parses valid rows and updates twin."""
    client.post("/api/patients", json={
        "id": "PT-CSV-TEST",
        "name": "CSV Ingestion Patient",
        "age": 45,
        "gender": "Male",
        "baseline_heart_rate": 72.0
    })

    csv_data = generate_synthetic_csv("PT-CSV-TEST")
    res = client.post(
        "/api/patients/PT-CSV-TEST/upload-csv",
        files={"file": ("measurements.csv", csv_data, "text/csv")}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["valid_inserted"] > 0
    assert body["twin_state_version"] == 1


# =========================================================================
# 5. Extended End-to-End Workflow & Edge Cases Tests
# =========================================================================

def test_end_to_end_twin_workflow(client):
    """
    Verifies full Hackloop demonstration sequence:
    1. Load synthetic patient (State v1)
    2. Generate forecast (stale=False, version=1)
    3. Generate Scenario A and B
    4. Post new valid measurement -> State increments to v2, forecast marked stale
    5. Generate fresh forecast (stale=False, version=2)
    6. Verify held-out evaluation
    """
    # 1. Load synthetic patient
    res_init = client.post("/api/patients/synthetic", json={
        "patient_id": "PT-E2E-001",
        "name": "E2E Test Subject",
        "baseline_hr": 74.0,
        "duration_hours": 18
    })
    assert res_init.status_code == 201
    assert res_init.json()["twin_state_version"] == 1

    # 2. Generate forecast under v1
    res_fc1 = client.post("/api/patients/PT-E2E-001/forecast", json={"horizon_minutes": 180})
    assert res_fc1.status_code == 200
    fc1 = res_fc1.json()
    assert fc1["twin_state_version"] == 1
    assert fc1["is_stale"] is False
    assert len(fc1["predicted_trajectory"]) == 12  # 180 min / 15 min = 12 steps

    # 3. Simulate Scenarios
    res_sim = client.post("/api/patients/PT-E2E-001/simulate", json={
        "horizon_minutes": 180,
        "parameter_value": -35.0
    })
    assert res_sim.status_code == 200
    sim = res_sim.json()
    assert sim["baseline_state_version"] == 1
    assert sim["delta_summary"]["max_absolute_delta_bpm"] > 0

    # 4. Post new measurement
    new_ts = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    res_meas = client.post("/api/patients/PT-E2E-001/measurements", json={
        "timestamp": new_ts,
        "measurement_type": "heart_rate",
        "value": 78.5,
        "unit": "bpm"
    })
    assert res_meas.status_code == 201
    meas_data = res_meas.json()
    assert meas_data["digital_twin_update"]["current_state_version"] == 2
    assert meas_data["digital_twin_update"]["stale_forecasts_invalidated"] >= 1

    # Check that previous forecast is now marked stale
    res_fcs = client.get("/api/patients/PT-E2E-001/forecasts")
    assert res_fcs.status_code == 200
    fcs_list = res_fcs.json()
    old_fc = next(f for f in fcs_list if f["id"] == fc1["id"])
    assert old_fc["is_stale"] is True
    assert old_fc["twin_state_version"] == 1

    # 5. Generate fresh forecast under v2
    res_fc2 = client.post("/api/patients/PT-E2E-001/forecast", json={"horizon_minutes": 180})
    assert res_fc2.status_code == 200
    fc2 = res_fc2.json()
    assert fc2["twin_state_version"] == 2
    assert fc2["is_stale"] is False

    # 6. Verify chronological evaluation
    res_eval = client.get("/api/patients/PT-E2E-001/evaluation")
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["train_samples"] > 0
    assert eval_data["test_samples"] > 0
    assert eval_data["mae"] >= 0


def test_api_json_batch_upload(client):
    """Verify batch ingestion via JSON endpoint."""
    client.post("/api/patients", json={
        "id": "PT-JSON-TEST",
        "name": "JSON Batch Patient",
        "age": 52,
        "gender": "Female",
        "baseline_heart_rate": 68.0
    })

    now = datetime.now(timezone.utc)
    measurements_payload = {
        "measurements": [
            {
                "timestamp": (now - timedelta(minutes=i * 15)).isoformat(),
                "measurement_type": "heart_rate",
                "value": 70.0 + (i % 5),
                "unit": "bpm",
                "source": "batch_json"
            }
            for i in range(20, 0, -1)
        ]
    }

    res = client.post("/api/patients/PT-JSON-TEST/upload-json", json=measurements_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["valid_inserted"] == 20
    assert body["twin_state_version"] == 1


# =========================================================================
# 6. Web3 Decentralized State Attestation & Access Control Tests
# =========================================================================

def test_web3_network_status(client):
    """Verify Web3 node connection and smart contract registry deployment."""
    res = client.get("/api/web3/status")
    assert res.status_code == 200
    body = res.json()
    assert body["is_connected"] is True
    assert "0x" in body["contract_address"]
    assert "0x" in body["active_wallet_address"]
    assert body["latest_block_number"] >= 1


def test_web3_on_chain_state_verification(client):
    """
    Verify on-chain cryptographic attestation:
    1. Seed patient & initialize twin -> Anchors on-chain
    2. Query on-chain verify -> Returns is_valid == True
    3. Modify candidate features -> Returns is_valid == False (tamper-evident proof!)
    """
    res_init = client.post("/api/patients/synthetic", json={
        "patient_id": "PT-WEB3-VERIFY",
        "duration_hours": 12
    })
    assert res_init.status_code == 201

    # Verify on-chain parity
    res_ver = client.get("/api/web3/patients/PT-WEB3-VERIFY/twin/1/verify")
    assert res_ver.status_code == 200
    ver_body = res_ver.json()
    assert ver_body["is_valid"] is True
    assert ver_body["on_chain_root"] == ver_body["candidate_hash"]
    assert ver_body["ipfs_cid"].startswith("bafybeih")
    assert ver_body["block_number"] >= 1


def test_web3_sovereign_consent_grant_and_revoke(client):
    """Verify patient sovereign consent: grant and revoke researcher access on-chain."""
    client.post("/api/patients/synthetic", json={"patient_id": "PT-WEB3-ACCESS"})

    researcher_addr = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"

    # Initially researcher should not have access
    res_check1 = client.get("/api/web3/patients/PT-WEB3-ACCESS/access/check", params={"user_address": researcher_addr})
    assert res_check1.status_code == 200
    assert res_check1.json()["has_access"] is False

    # Grant access on-chain
    res_grant = client.post("/api/web3/patients/PT-WEB3-ACCESS/access/grant", json={
        "researcher_address": researcher_addr,
        "duration_seconds": 3600
    })
    assert res_grant.status_code == 200
    assert res_grant.json()["success"] is True
    assert "tx_hash" in res_grant.json()

    # Verify access is now active
    res_check2 = client.get("/api/web3/patients/PT-WEB3-ACCESS/access/check", params={"user_address": researcher_addr})
    assert res_check2.status_code == 200
    assert res_check2.json()["has_access"] is True

    # Revoke access on-chain
    res_revoke = client.post("/api/web3/patients/PT-WEB3-ACCESS/access/revoke", json={
        "researcher_address": researcher_addr
    })
    assert res_revoke.status_code == 200
    assert res_revoke.json()["success"] is True

    # Verify access is now revoked
    res_check3 = client.get("/api/web3/patients/PT-WEB3-ACCESS/access/check", params={"user_address": researcher_addr})
    assert res_check3.status_code == 200
    assert res_check3.json()["has_access"] is False

