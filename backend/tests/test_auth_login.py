"""
Automated Test Suite for Authentication & Login in Sovereign Health Twin.
Tests:
- Successful login for registered users
- Successful login for standard demo credentials (demo@patient.org / DemoPassword123!)
- Rejection of invalid passwords (401 Unauthorized)
- Rejection of nonexistent users (401 Unauthorized)
- Rejection of deactivated accounts (401 Unauthorized)
- Token-authenticated session retrieval via GET /api/auth/me
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import os

# Ensure backend dir is on sys.path
_cur = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_cur, ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.main import app
from app.database.connection import Base, get_db
from app.models.user import User
from app.models.patient import Patient
from app.services.auth import hash_password

# Isolated in-memory test database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    # Seed test users
    db = TestingSessionLocal()

    # 1. Registered active user
    u1 = User(
        id="USR-TEST-01",
        email="sarah.jenkins@hospital.org",
        hashed_password=hash_password("PatientPassword123!"),
        full_name="Sarah Jenkins",
        is_active=True,
        patient_id="PT-TEST-01"
    )
    p1 = Patient(
        id="PT-TEST-01",
        name="Sarah Jenkins",
        age=52,
        gender="Female",
        baseline_heart_rate=72.0,
        is_synthetic=False
    )

    # 2. Standard demo user
    u_demo = User(
        id="USR-DEMO",
        email="demo@patient.org",
        hashed_password=hash_password("DemoPassword123!"),
        full_name="Alice M. Taylor (Demo)",
        is_active=True,
        patient_id="PT-DEMO-001"
    )
    p_demo = Patient(
        id="PT-DEMO-001",
        name="Alice M. Taylor",
        age=56,
        gender="Female",
        baseline_heart_rate=72.0,
        is_synthetic=True
    )

    # 3. Deactivated user
    u_inactive = User(
        id="USR-INACTIVE",
        email="inactive.user@hospital.org",
        hashed_password=hash_password("InactivePassword123!"),
        full_name="Inactive Account",
        is_active=False,
        patient_id="PT-INACTIVE"
    )

    db.add_all([u1, p1, u_demo, p_demo, u_inactive])
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_login_success_registered_user(client):
    """Verifies that a registered user with correct email and password logs in successfully."""
    res = client.post(
        "/api/auth/login",
        json={"email": "sarah.jenkins@hospital.org", "password": "PatientPassword123!"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sarah.jenkins@hospital.org"
    assert data["user"]["full_name"] == "Sarah Jenkins"
    assert data["user"]["patient_id"] == "PT-TEST-01"


def test_login_success_case_insensitive_and_trimmed(client):
    """Verifies email whitespace trimming and case insensitivity."""
    res = client.post(
        "/api/auth/login",
        json={"email": "  SARAH.JENKINS@hospital.org  ", "password": "PatientPassword123!"}
    )
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "sarah.jenkins@hospital.org"


def test_login_success_standard_demo_credentials(client):
    """Verifies that standard demo credentials (demo@patient.org / DemoPassword123!) log in successfully."""
    res = client.post(
        "/api/auth/login",
        json={"email": "demo@patient.org", "password": "DemoPassword123!"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "demo@patient.org"
    assert data["user"]["patient_id"] == "PT-DEMO-001"


def test_login_invalid_password(client):
    """Verifies that providing an incorrect password returns 401 Unauthorized."""
    res = client.post(
        "/api/auth/login",
        json={"email": "sarah.jenkins@hospital.org", "password": "WrongPassword123!"}
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_login_nonexistent_user(client):
    """Verifies that an un-registered email returns 401 Unauthorized without leaking existence."""
    res = client.post(
        "/api/auth/login",
        json={"email": "unknown.user.999@notfound.org", "password": "SomePassword123!"}
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_login_inactive_user(client):
    """Verifies that deactivated accounts cannot log in even with the correct password."""
    res = client.post(
        "/api/auth/login",
        json={"email": "inactive.user@hospital.org", "password": "InactivePassword123!"}
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_login_missing_or_empty_credentials(client):
    """Verifies that requests with empty or missing email/password are rejected."""
    # Missing password
    res1 = client.post("/api/auth/login", json={"email": "sarah.jenkins@hospital.org"})
    assert res1.status_code == 422

    # Missing email
    res2 = client.post("/api/auth/login", json={"password": "PatientPassword123!"})
    assert res2.status_code == 400 or res2.status_code == 422


def test_authenticated_get_me_session(client):
    """Verifies that the issued JWT token can be used to query /api/auth/me."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "sarah.jenkins@hospital.org", "password": "PatientPassword123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Call /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    user = me_res.json()
    assert user["id"] == "USR-TEST-01"
    assert user["email"] == "sarah.jenkins@hospital.org"
    assert user["patient_id"] == "PT-TEST-01"
