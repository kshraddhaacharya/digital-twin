"""
Comprehensive Timezone and IST Integration Tests for Sovereign Health Twin.
Verifies UTC storage, 'Z' ISO 8601 API serialization, Asia/Kolkata (IST) conversion accuracy,
boundary day rollovers, and calendar date-only preservation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.connection import Base, get_db
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.models.twin_state import TwinState
from app.utils.datetime_utils import to_utc_iso, parse_utc_datetime, ensure_utc_datetime

# Isolated test engine with StaticPool
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_to_utc_iso_serialization():
    """Verifies that naive and aware datetimes, as well as ISO strings, normalize to UTC ending with 'Z'."""
    # 1. Naive datetime from SQLite
    naive_dt = datetime(2026, 10, 28, 17, 37, 0)
    assert to_utc_iso(naive_dt) == "2026-10-28T17:37:00Z"

    # 2. Aware UTC datetime
    aware_dt = datetime(2026, 10, 28, 17, 37, 0, tzinfo=timezone.utc)
    assert to_utc_iso(aware_dt) == "2026-10-28T17:37:00Z"

    # 3. Naive ISO string without Z
    assert to_utc_iso("2026-10-28T17:37:00") == "2026-10-28T17:37:00Z"

    # 4. Space-separated SQL timestamp string
    assert to_utc_iso("2026-10-28 17:37:00") == "2026-10-28T17:37:00Z"

    # 5. String already ending with Z
    assert to_utc_iso("2026-10-28T17:37:00Z") == "2026-10-28T17:37:00Z"

    # 6. Date-only string MUST NOT be altered or converted into a timestamp
    assert to_utc_iso("2026-10-28") == "2026-10-28"

    # 7. None handling
    assert to_utc_iso(None) is None


def test_measurement_api_returns_utc_with_z(client, db_session):
    """Verifies that measurement submission and retrieval return unambiguous UTC timestamps with 'Z'."""
    test_patient_id = "PT-TIMEZONE-TEST"

    # Create patient
    p = Patient(
        id=test_patient_id,
        name="Timezone Audit Patient",
        age=45,
        gender="Female",
        baseline_heart_rate=72.0,
        is_synthetic=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(p)
    db_session.commit()

    # Submit observation at 17:37:00 UTC (which corresponds to 11:07 PM IST)
    payload = {
        "timestamp": "2026-10-28T17:37:00Z",
        "measurement_type": "heart_rate",
        "value": 78.0,
        "unit": "bpm",
        "source": "clinical_monitor",
        "context": "resting"
    }

    res = client.post(f"/api/patients/{test_patient_id}/measurements", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()

    # Verify response body timestamp ends with 'Z'
    meas = data["measurement"]
    assert meas["timestamp"] == "2026-10-28T17:37:00Z"
    assert meas["created_at"].endswith("Z")

    # Fetch measurements list
    res_list = client.get(f"/api/patients/{test_patient_id}/measurements")
    assert res_list.status_code == 200
    measurements = res_list.json()
    assert len(measurements) >= 1
    target = next((m for m in measurements if m["id"] == meas["id"]), None)
    assert target is not None
    assert target["timestamp"] == "2026-10-28T17:37:00Z"

    # Fetch active twin state
    res_twin = client.get(f"/api/patients/{test_patient_id}/twin")
    assert res_twin.status_code == 200
    twin = res_twin.json()
    assert twin["timestamp_latest_observation"] == "2026-10-28T17:37:00Z"
    assert twin["created_at"].endswith("Z")


def test_midnight_day_rollover_ist():
    """
    Verifies that a UTC timestamp near midnight (e.g. 20:30 UTC on 28 Oct)
    correctly advances to 02:00 AM on 29 Oct in Indian Standard Time (UTC+05:30).
    """
    utc_time = datetime(2026, 10, 28, 20, 30, 0, tzinfo=timezone.utc)
    # Target in IST is +5h30m -> 2026-10-29 02:00:00
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_time = utc_time.astimezone(ist_offset)

    assert ist_time.year == 2026
    assert ist_time.month == 10
    assert ist_time.day == 29
    assert ist_time.hour == 2
    assert ist_time.minute == 0


def test_date_only_values_preserved_without_day_shifting():
    """
    Verifies that calendar date-only strings such as report dates, cycle dates,
    and dates of birth are NEVER shifted to another day.
    """
    report_date = "2026-10-28"
    assert to_utc_iso(report_date) == "2026-10-28"

    cycle_start = "2026-10-15"
    assert to_utc_iso(cycle_start) == "2026-10-15"

    dob = "1980-03-22"
    assert to_utc_iso(dob) == "1980-03-22"

