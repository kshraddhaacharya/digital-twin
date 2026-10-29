"""
Automated Test Suite for Medical Report Persistence and History in Sovereign Health Twin.
Verifies all 12 persistence, retrieval, isolation, duplication, and Web3 integrity requirements.
Uses strictly synthetic, fictional medical reports (NO real patient data).
"""

import io
import os
import sys
import glob
import hashlib
import pytest
from unittest.mock import patch
from datetime import datetime, timezone

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.connection import Base, get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.report import MedicalReport
from app.services.auth import create_access_token, hash_password
from app.services.report_classifier import ReportCategory
from app.services.ocr_service import register_ocr_handler


# Isolated test database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_synthetic_pdf(text_lines: list) -> bytes:
    """Generates a minimal, syntactically valid PDF with digital character stream."""
    stream_lines = []
    for line in text_lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_lines.append(f"({safe_line}) Tj T*")
    stream_content = "BT /F1 12 Tf 14 TL 50 750 Td\n" + "\n".join(stream_lines) + "\nET"
    stream_bytes = stream_content.encode("latin-1")
    stream_len = len(stream_bytes)

    obj1 = b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
    obj2 = b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
    obj3 = b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources <</Font <</F1 4 0 R>>>> /Contents 5 0 R>> endobj\n"
    obj4 = b"4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
    obj5 = f"5 0 obj <</Length {stream_len}>> stream\n".encode("latin-1") + stream_bytes + b"\nendstream\nendobj\n"

    header = b"%PDF-1.4\n"
    offsets = [0]
    curr = len(header)
    for obj in [obj1, obj2, obj3, obj4, obj5]:
        offsets.append(curr)
        curr += len(obj)

    xref_offset = curr
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for o in offsets[1:]:
        xref += f"{o:010d} 00000 n \n".encode("ascii")
    trailer = f"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")

    return header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer


@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)
    register_ocr_handler(None)
    for f in glob.glob("uploads/reports/USR-PTEST-*.pdf"):
        try:
            os.remove(f)
        except OSError:
            pass


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def auth_context():
    db = TestingSessionLocal()
    user1 = User(
        id="USR-PTEST-01",
        email="patient_alpha@research.org",
        hashed_password=hash_password("SecurePassword123!"),
        full_name="Patient Alpha (Synthetic)",
        patient_id="PT-PTEST-01",
    )
    patient1 = Patient(
        id="PT-PTEST-01",
        name="Patient Alpha (Synthetic)",
        age=54,
        gender="Female",
        baseline_heart_rate=72.0,
        is_synthetic=False,
    )
    user2 = User(
        id="USR-PTEST-02",
        email="patient_beta@research.org",
        hashed_password=hash_password("SecurePassword123!"),
        full_name="Patient Beta (Synthetic)",
        patient_id="PT-PTEST-02",
    )
    patient2 = Patient(
        id="PT-PTEST-02",
        name="Patient Beta (Synthetic)",
        age=48,
        gender="Male",
        baseline_heart_rate=68.0,
        is_synthetic=False,
    )
    db.add_all([user1, patient1, user2, patient2])
    db.commit()
    db.close()

    token1 = create_access_token({"sub": "USR-PTEST-01", "email": "patient_alpha@research.org"})
    token2 = create_access_token({"sub": "USR-PTEST-02", "email": "patient_beta@research.org"})

    return {
        "user1": {"token": token1, "patient_id": "PT-PTEST-01", "user_id": "USR-PTEST-01"},
        "user2": {"token": token2, "patient_id": "PT-PTEST-02", "user_id": "USR-PTEST-02"},
    }


# ==============================================================================
# Scenario 1: Upload and Immediate Persistence in Authoritative Database
# ==============================================================================
def test_upload_and_immediate_persistence(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "CLINICAL BIOCHEMISTRY ONCOLOGY LABORATORY",
        "Serum Tumour Marker Panel",
        "Patient: Patient Alpha (Synthetic)",
        "Prostate Specific Antigen (Total PSA): 7.40 ng/mL (Ref: 0.0 - 4.0 ng/mL)",
        "Carcinoembryonic Antigen (CEA): 1.8 ng/mL (Ref: 0.0 - 3.0 ng/mL)",
        "Impression: Mild PSA elevation noted."
    ])
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("serum_markers_alpha.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Baseline Serum Tumour Markers", "report_date": "2026-10-25"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res.status_code == 201
    payload = res.json()

    # Verify persistence status and payload
    assert payload["persisted"] is True
    assert payload["is_duplicate"] is False
    assert "report" in payload

    rep = payload["report"]
    report_id = rep["id"]
    assert isinstance(report_id, int)
    assert rep["patient_id"] == "PT-PTEST-01"
    assert rep["file_hash_sha256"] == expected_hash
    assert rep["report_category"] == ReportCategory.TUMOUR_MARKERS
    assert rep["processing_status"] == "Clinically structured"
    assert "upload_timestamp_ist" in rep
    assert "+05:30" in rep["upload_timestamp_ist"] or "IST" in rep["upload_timestamp_ist"]
    assert rep["storage_reference"] is not None

    # Verify direct database entry via isolated DB session
    db = TestingSessionLocal()
    db_record = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    assert db_record is not None
    assert db_record.patient_id == "PT-PTEST-01"
    assert db_record.file_hash_sha256 == expected_hash
    assert db_record.report_category == ReportCategory.TUMOUR_MARKERS
    assert db_record.clinical_summary is not None
    assert "7.4" in str(db_record.structured_findings)
    db.close()


# ==============================================================================
# Scenario 2: Refresh Page and Verify Persistence (No State Loss)
# ==============================================================================
def test_refresh_page_and_verify_persistence(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "CLINICAL LABORATORY REPORT",
        "Serum Tumour Marker Panel",
        "Prostate Specific Antigen (Total PSA): 7.40 ng/mL (Ref: 0.0 - 4.0 ng/mL)"
    ])
    # 1. Upload
    up_res = test_client.post(
        "/api/reports/upload",
        files={"file": ("refresh_test_report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Pre-Refresh Health Report", "report_date": "2026-10-24"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert up_res.status_code == 201
    created_id = up_res.json()["report"]["id"]

    # 2. Simulate refresh: query list of reports from backend API without client state
    get_res = test_client.get(
        "/api/reports/",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert get_res.status_code == 200
    reports = get_res.json()
    assert len(reports) >= 1

    matched = [r for r in reports if r["id"] == created_id]
    assert len(matched) == 1
    persisted = matched[0]

    assert persisted["title"] == "Pre-Refresh Health Report"
    assert persisted["report_category"] == ReportCategory.TUMOUR_MARKERS
    assert persisted["processing_status"] == "Clinically structured"
    assert persisted["clinical_summary"] is not None
    assert len(persisted["structured_findings"]["tumor_markers"]) == 1
    assert persisted["upload_timestamp_ist"] is not None


# ==============================================================================
# Scenario 3: Navigate Away and Return (Individual Report Retrieval)
# ==============================================================================
def test_navigate_away_and_return(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "Surgical Pathology Report - Final Diagnosis",
        "Specimen Received: Right breast biopsy",
        "Invasive Ductal Carcinoma, Nottingham Histologic Grade: Grade 2",
        "Pathologic Stage: pT2 pN0"
    ])
    up_res = test_client.post(
        "/api/reports/upload",
        files={"file": ("biopsy_nav.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Biopsy Examination", "report_date": "2026-10-22"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert up_res.status_code == 201
    rep_id = up_res.json()["report"]["id"]

    # Directly fetch report details as done upon re-opening Health Records
    single_res = test_client.get(
        f"/api/reports/{rep_id}",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert single_res.status_code == 200
    details = single_res.json()
    assert details["id"] == rep_id
    assert details["report_category"] == ReportCategory.HISTOPATHOLOGY_BIOPSY
    assert details["structured_findings"]["diagnosis"]["tumor_grade"] == "Grade 2"


# ==============================================================================
# Scenario 4: Multiple Reports for Same Patient Accumulate in Order
# ==============================================================================
def test_multiple_reports_for_same_patient(test_client, auth_context):
    reports_data = [
        ("CBC Blood Test", "Complete Blood Count\nHemoglobin: 13.5 g/dL\nWBC: 6.8 x10^3/uL", "2026-10-10"),
        ("Biopsy Specimen", "Surgical Pathology Report\nInvasive ductal carcinoma, Grade 1", "2026-10-15"),
        ("PSA Test", "Serum Tumour Marker Panel\nTotal PSA: 5.2 ng/mL (Ref: 0-4 ng/mL)", "2026-10-20"),
    ]
    created_ids = []
    for title, content, date in reports_data:
        b = generate_synthetic_pdf([content])
        res = test_client.post(
            "/api/reports/upload",
            files={"file": (f"{title.replace(' ', '_').lower()}.pdf", b, "application/pdf")},
            data={"title": title, "report_date": date},
            headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
        )
        assert res.status_code == 201
        created_ids.append(res.json()["report"]["id"])

    # Retrieve all
    list_res = test_client.get(
        "/api/reports/",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert list_res.status_code == 200
    all_reps = list_res.json()
    user_rep_ids = [r["id"] for r in all_reps]
    for cid in created_ids:
        assert cid in user_rep_ids


# ==============================================================================
# Scenario 5: History Isolation Between Different Patients
# ==============================================================================
def test_patient_history_isolation(test_client, auth_context):
    # User 1 uploads a confidential report
    b1 = generate_synthetic_pdf(["Confidential Molecular Test\nEGFR Mutation: L858R detected"])
    res1 = test_client.post(
        "/api/reports/upload",
        files={"file": ("alpha_molecular.pdf", b1, "application/pdf")},
        data={"title": "Patient Alpha Molecular Genetics", "report_date": "2026-10-25"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res1.status_code == 201
    rep1_id = res1.json()["report"]["id"]

    # User 2 queries their own reports list
    res2 = test_client.get(
        "/api/reports/",
        headers={"Authorization": f"Bearer {auth_context['user2']['token']}"}
    )
    assert res2.status_code == 200
    user2_reports = res2.json()
    assert all(r["patient_id"] == "PT-PTEST-02" for r in user2_reports)
    assert not any(r["id"] == rep1_id for r in user2_reports)

    # User 2 attempts to directly access User 1's report by ID
    res_forbidden = test_client.get(
        f"/api/reports/{rep1_id}",
        headers={"Authorization": f"Bearer {auth_context['user2']['token']}"}
    )
    assert res_forbidden.status_code == 403

    # User 2 attempts to query User 1's patient_id via parameter
    res_cross_pt = test_client.get(
        "/api/reports/?patient_id=PT-PTEST-01",
        headers={"Authorization": f"Bearer {auth_context['user2']['token']}"}
    )
    assert res_cross_pt.status_code == 403


# ==============================================================================
# Scenario 6: Reprocessing Existing Report In-Place (No Duplicate Row)
# ==============================================================================
def test_reprocessing_existing_report(test_client, auth_context):
    b = generate_synthetic_pdf([
        "Serum Tumour Marker Panel",
        "Prostate Specific Antigen (Total PSA): 6.80 ng/mL"
    ])
    up_res = test_client.post(
        "/api/reports/upload",
        files={"file": ("reprocess_test.pdf", b, "application/pdf")},
        data={"title": "Initial Upload to Reprocess", "report_date": "2026-10-26"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert up_res.status_code == 201
    rep_id = up_res.json()["report"]["id"]

    db_before = TestingSessionLocal()
    count_before = db_before.query(MedicalReport).count()
    db_before.close()

    # Reprocess
    re_res = test_client.post(
        f"/api/reports/{rep_id}/reprocess",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert re_res.status_code == 200
    rep_after = re_res.json()["report"]
    assert rep_after["id"] == rep_id

    # Verify no duplicate row was created
    db_after = TestingSessionLocal()
    count_after = db_after.query(MedicalReport).count()
    db_after.close()
    assert count_after == count_before


# ==============================================================================
# Scenario 7: Handling Duplicate Uploads Safely
# ==============================================================================
def test_handling_duplicate_uploads(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "CLINICAL BIOCHEMISTRY ONCOLOGY LABORATORY",
        "Serum Tumour Marker Panel",
        "Patient: Patient Alpha (Synthetic)",
        "Prostate Specific Antigen (Total PSA): 7.40 ng/mL (Ref: 0.0 - 4.0 ng/mL)",
        "Carcinoembryonic Antigen (CEA): 1.8 ng/mL (Ref: 0.0 - 3.0 ng/mL)",
        "Impression: Mild PSA elevation noted."
    ])

    # First upload
    res1 = test_client.post(
        "/api/reports/upload",
        files={"file": ("colon_polyp.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Colon Polyp Biopsy", "report_date": "2026-10-18"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["is_duplicate"] is False
    report_id = data1["report"]["id"]

    # Second upload with identical bytes
    res2 = test_client.post(
        "/api/reports/upload",
        files={"file": ("colon_polyp_reupload.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Colon Polyp Duplicate Attempt", "report_date": "2026-10-18"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_duplicate"] is True
    assert data2["report"]["id"] == report_id
    assert "already been analyzed" in data2["message"] or "Existing" in data2["message"]

    # Verify DB only has 1 record for this hash
    db = TestingSessionLocal()
    matches = db.query(MedicalReport).filter(MedicalReport.patient_id == "PT-PTEST-01").all()
    assert len(matches) == 1
    db.close()


# ==============================================================================
# Scenario 8: History Retrieval for Patients with Zero Reports
# ==============================================================================
def test_zero_reports_history_returns_valid_empty_list(test_client, auth_context):
    res = test_client.get(
        "/api/reports/",
        headers={"Authorization": f"Bearer {auth_context['user2']['token']}"}
    )
    assert res.status_code == 200
    assert res.json() == []


# ==============================================================================
# Scenario 9: Web3 Cryptographic Integrity Check Verification
# ==============================================================================
def test_web3_cryptographic_integrity_verification(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "IMMUNOHISTOCHEMISTRY (IHC) REPORT",
        "Biomarkers: ER Positive 95%, PR Positive 80%, HER2 Negative (Score 1+)"
    ])
    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("ihc_tamper_test.pdf", pdf_bytes, "application/pdf")},
        data={"title": "IHC Panel Test", "report_date": "2026-10-21"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res.status_code == 201
    rep_id = res.json()["report"]["id"]

    # 1. Verification of pristine file
    verify_res = test_client.get(
        f"/api/reports/{rep_id}/verify-integrity",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["is_tamper_free"] is True
    assert vdata["file_exists"] is True
    assert vdata["stored_sha256"] == vdata["recomputed_sha256"]
    assert "Tamper-free" in vdata["verification_status"] or "Cryptographically verified" in vdata["verification_status"]

    # 2. Simulate file tampering on disk
    db = TestingSessionLocal()
    db_rep = db.query(MedicalReport).filter(MedicalReport.id == rep_id).first()
    storage_path = db_rep.file_path
    db.close()

    assert os.path.exists(storage_path)
    with open(storage_path, "wb") as f:
        f.write(b"%PDF-1.4 TAMPERED FILE DATA")

    tamper_res = test_client.get(
        f"/api/reports/{rep_id}/verify-integrity",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert tamper_res.status_code == 200
    tdata = tamper_res.json()
    assert tdata["is_tamper_free"] is False
    assert tdata["file_exists"] is True
    assert tdata["stored_sha256"] != tdata["recomputed_sha256"]
    assert "Tamper" in tdata["verification_status"]

    # 3. Simulate missing file on disk
    os.remove(storage_path)
    missing_res = test_client.get(
        f"/api/reports/{rep_id}/verify-integrity",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert missing_res.status_code == 200
    mdata = missing_res.json()
    assert mdata["is_tamper_free"] is False
    assert mdata["file_exists"] is False
    assert "missing" in mdata["verification_status"].lower()


# ==============================================================================
# Scenario 10: Database Transaction Rollback on Save Failure
# ==============================================================================
def test_database_transaction_rollback_on_save_failure(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "Serum Tumour Marker Panel",
        "Prostate Specific Antigen: 4.5 ng/mL"
    ])

    with patch.object(Session, "commit", side_effect=Exception("Simulated SQLite Disk I/O Failure")):
        res = test_client.post(
            "/api/reports/upload",
            files={"file": ("rollback_test.pdf", pdf_bytes, "application/pdf")},
            data={"title": "Rollback Test Report", "report_date": "2026-10-25"},
            headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
        )
        assert res.status_code == 500
        err = res.json()["detail"]
        assert "database persistence failed" in err.lower()
        assert "Simulated SQLite Disk I/O Failure" in err

    # Ensure no broken record exists in database
    db = TestingSessionLocal()
    broken = db.query(MedicalReport).filter(MedicalReport.title == "Rollback Test Report").all()
    assert len(broken) == 0
    db.close()


# ==============================================================================
# Scenario 11: Ordering by Upload Timestamp (Newest Upload First)
# ==============================================================================
def test_ordering_by_upload_timestamp(test_client, auth_context):
    # Upload Report 1 (clinical date = 2026-10-25)
    b1 = generate_synthetic_pdf(["Report One\nNormal findings"])
    res1 = test_client.post(
        "/api/reports/upload",
        files={"file": ("rep1.pdf", b1, "application/pdf")},
        data={"title": "Recent Clinical Date Report", "report_date": "2026-10-25"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res1.status_code == 201
    id1 = res1.json()["report"]["id"]

    # Upload Report 2 second (clinical date = 2018-01-01, an older report uploaded later)
    b2 = generate_synthetic_pdf(["Report Two\nHistorical findings"])
    res2 = test_client.post(
        "/api/reports/upload",
        files={"file": ("rep2.pdf", b2, "application/pdf")},
        data={"title": "Historical 2018 Report Uploaded Today", "report_date": "2018-01-01"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res2.status_code == 201
    id2 = res2.json()["report"]["id"]

    # Retrieve history
    list_res = test_client.get(
        "/api/reports/",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert list_res.status_code == 200
    reps = list_res.json()
    assert len(reps) >= 2

    # Newest uploaded report (id2) MUST be first in list
    assert reps[0]["id"] == id2
    assert reps[1]["id"] == id1


# ==============================================================================
# Scenario 12: Category Filtering and Pagination on Persisted Reports
# ==============================================================================
def test_category_filtering_and_pagination(test_client, auth_context):
    # Upload 1 Tumour Marker, 1 Biopsy
    tm_pdf = generate_synthetic_pdf(["Serum Tumour Marker Panel\nTotal PSA: 5.5 ng/mL"])
    bx_pdf = generate_synthetic_pdf(["Surgical Pathology Report\nInvasive ductal carcinoma"])

    res_tm = test_client.post(
        "/api/reports/upload",
        files={"file": ("filt_tm.pdf", tm_pdf, "application/pdf")},
        data={"title": "Filtering PSA Test", "report_date": "2026-10-20"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res_tm.status_code == 201
    tm_id = res_tm.json()["report"]["id"]

    res_bx = test_client.post(
        "/api/reports/upload",
        files={"file": ("filt_bx.pdf", bx_pdf, "application/pdf")},
        data={"title": "Filtering Biopsy Test", "report_date": "2026-10-21"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res_bx.status_code == 201
    bx_id = res_bx.json()["report"]["id"]

    # Filter by category = tumour_markers
    res_filt = test_client.get(
        f"/api/reports/?category={ReportCategory.TUMOUR_MARKERS}",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res_filt.status_code == 200
    filt_list = res_filt.json()
    assert all(r["report_category"] == ReportCategory.TUMOUR_MARKERS for r in filt_list)
    assert any(r["id"] == tm_id for r in filt_list)
    assert not any(r["id"] == bx_id for r in filt_list)

    # Test pagination (limit=1, offset=0 and offset=1)
    page1 = test_client.get(
        "/api/reports/?limit=1&offset=0",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    ).json()
    page2 = test_client.get(
        "/api/reports/?limit=1&offset=1",
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    ).json()

    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0]["id"] != page2[0]["id"]


# ==============================================================================
# Scenario 13: Direct Non-Trailing-Slash Route & Cross-Field Search Verification
# ==============================================================================
def test_reports_endpoint_no_redirect_without_trailing_slash(auth_context):
    """Verifies that /api/reports (without trailing slash) does not return 307 redirect."""
    client_no_redirect = TestClient(app, follow_redirects=False)

    # Test without slash
    r_no_slash = client_no_redirect.get(
        "/api/reports",
        params={"patient_id": auth_context["user1"]["patient_id"]},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert r_no_slash.status_code == 200
    assert isinstance(r_no_slash.json(), list)

    # Test with slash
    r_with_slash = client_no_redirect.get(
        "/api/reports/",
        params={"patient_id": auth_context["user1"]["patient_id"]},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert r_with_slash.status_code == 200
    assert isinstance(r_with_slash.json(), list)


def test_reports_keyword_search_across_clinical_summary_and_findings(test_client, auth_context):
    """Verifies keyword search across titles, summaries, findings, and extracted text."""
    pdf = generate_synthetic_pdf([
        "Oncology Molecular Panel",
        "Clinical Diagnosis: Metastatic adenoid cystic carcinoma",
        "Next Generation Sequencing: BRAF V600E mutation identified"
    ])
    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("onco_search.pdf", pdf, "application/pdf")},
        data={"title": "Targeted Genomic Assessment", "report_date": "2026-10-26"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert res.status_code == 201

    # Search by keyword in summary/findings ("carcinoma") without trailing slash
    search_res = test_client.get(
        "/api/reports",
        params={"patient_id": auth_context["user1"]["patient_id"], "search": "carcinoma"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert any("carcinoma" in (r.get("clinical_summary", "") + r.get("title", "") + r.get("extracted_text", "")).lower() for r in results)

    # Search for non-existent keyword
    search_none = test_client.get(
        "/api/reports",
        params={"patient_id": auth_context["user1"]["patient_id"], "search": "xyznonexistentterm123"},
        headers={"Authorization": f"Bearer {auth_context['user1']['token']}"}
    )
    assert search_none.status_code == 200
    assert len(search_none.json()) == 0


