import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.connection import Base, get_db

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def test_auth_registration_and_login():
    # 1. Register new user
    reg_payload = {
        "full_name": "Eleanor Vance",
        "email": "eleanor@example.com",
        "password": "SecurePassword123!",
        "age": 62,
        "gender": "Female",
        "height": 165.0,
        "body_weight": 68.0,
        "existing_conditions": "Mild Hypertension"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert "access_token" in data
    assert data["user"]["full_name"] == "Eleanor Vance"
    assert data["user"]["patient_id"].startswith("PT-")

    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get profile /me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "eleanor@example.com"
    assert me_res.json()["body_weight"] == 68.0

    # 3. Update profile
    update_res = client.put("/api/auth/profile", json={"body_weight": 67.5}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["body_weight"] == 67.5

    # 4. Login with credentials
    login_res = client.post("/api/auth/login", json={"email": "eleanor@example.com", "password": "SecurePassword123!"})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 5. Invalid password rejected
    bad_login = client.post("/api/auth/login", json={"email": "eleanor@example.com", "password": "WrongPassword"})
    assert bad_login.status_code == 401


def test_disease_tracker_flow():
    # Register user
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Marcus Aurelius",
        "email": "marcus@rome.org",
        "password": "Philosophy123!",
        "age": 58,
        "height": 178.0,
        "body_weight": 76.0
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add condition
    cond_res = client.post("/api/disease-tracker/conditions", json={
        "condition_name": "Hypertension",
        "severity": "mild",
        "status": "managed"
    }, headers=headers)
    assert cond_res.status_code == 201
    cond_id = cond_res.json()["id"]

    # Log entry
    log_res = client.post("/api/disease-tracker/logs", json={
        "condition_id": cond_id,
        "log_date": "2026-10-26",
        "metric_name": "Blood Pressure",
        "metric_value": 128.0,
        "metric_unit": "mmHg",
        "symptoms": "Felt slight tension after meeting"
    }, headers=headers)
    assert log_res.status_code == 201

    # Fetch logs
    list_res = client.get("/api/disease-tracker/logs", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Analytics check
    analytics_res = client.get("/api/disease-tracker/analytics", headers=headers)
    assert analytics_res.status_code == 200
    assert "cardiovascular" in analytics_res.json()
    assert analytics_res.json()["body_mass_index"]["bmi"] is not None


def test_menstrual_cycle_tracker():
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Clara Oswald",
        "email": "clara@tardis.com",
        "password": "RunYouCleverBoy1!",
        "gender": "Female",
        "age": 30
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Log cycle
    cycle_res = client.post("/api/cycle/log", json={
        "start_date": "2026-10-14",
        "cycle_length_days": 28,
        "period_length_days": 5,
        "flow_intensity": "medium",
        "symptoms": "Mild cramps on day 1"
    }, headers=headers)
    assert cycle_res.status_code == 201

    # Summary
    sum_res = client.get("/api/cycle/summary", headers=headers)
    assert sum_res.status_code == 200
    data = sum_res.json()
    assert data["has_data"] is True
    assert "current_phase" in data
    assert "days_until_next_period" in data

