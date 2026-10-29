"""
Automated Test Suite for Medical Report Classification, Extraction, and Clinical Summary
in Sovereign Health Twin.
Uses strictly synthetic, fictional medical reports (NO real patient data).
"""

import io
import json
import os
import glob
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.connection import Base, get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.report import MedicalReport
from app.services.auth import create_access_token, hash_password
from app.services.report_classifier import ReportCategory, classify_medical_report
from app.services.ocr_service import register_ocr_handler, extract_document_text
from app.services.report_extractor import extract_structured_findings
from app.services.report_summary import generate_grounded_clinical_summary


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
    for f in glob.glob("uploads/reports/USR-SYN-*.pdf"):
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
    user = User(
        id="USR-SYN-01",
        email="patient_synthetic@oncology-research.org",
        hashed_password=hash_password("SecurePassword123!"),
        full_name="Sarah Jenkins (Synthetic)",
        patient_id="PT-SYN-01",
    )
    patient = Patient(
        id="PT-SYN-01",
        name="Sarah Jenkins (Synthetic)",
        age=52,
        gender="Female",
        baseline_heart_rate=72.0,
        is_synthetic=False
    )
    db.add_all([user, patient])
    db.commit()
    db.close()
    token = create_access_token({"sub": "USR-SYN-01", "email": "patient_synthetic@oncology-research.org"})
    return {"token": token, "patient_id": "PT-SYN-01", "user_id": "USR-SYN-01"}


# ==============================================================================
# Case 1: Cancer-Related Pathology Report
# ==============================================================================
def test_cancer_pathology_report_extraction(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "DEPARTMENT OF SURGICAL PATHOLOGY",
        "Surgical Pathology Report - Final Diagnosis",
        "Patient: Fictional Patient Alpha (Synthetic)",
        "Specimen Received: Right breast core needle biopsy",
        "Clinical Indication: Palpable 2.2 cm retroareolar mass",
        "Gross Examination: Three fibrofatty core needle biopsies, 1.4 cm in aggregate length.",
        "Microscopic Diagnosis:",
        "Invasive Ductal Carcinoma, Nottingham Histologic Grade: Grade 2 (moderately differentiated).",
        "Surgical Margins: Negative for invasive carcinoma (> 5mm to inked border).",
        "Lymph Nodes: 0 of 2 sentinel lymph nodes involved by metastatic carcinoma.",
        "Lymphovascular Invasion: Not identified.",
        "Perineural Invasion: Not identified.",
        "Pathologic Stage: pT2 pN0.",
        "Comment: Formalin fixed paraffin embedded tissue."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("pathology_report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Right Breast Core Biopsy Report", "report_date": "2026-10-20"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    # 1. Classification
    assert data["report_category"] == ReportCategory.HISTOPATHOLOGY_BIOPSY
    assert data["classification_confidence"] == "high"
    assert "Histopathology" in data["category_name"]

    # 2. Status
    assert data["processing_status"] == "Clinically structured"

    # 3. Structured Findings
    sf = data["structured_findings"]
    assert sf["diagnosis"]["stated_diagnosis"] is not None
    assert "Invasive Ductal Carcinoma" in sf["diagnosis"]["stated_diagnosis"]
    assert "Grade 2" in sf["diagnosis"]["tumor_grade"]
    assert "Negative" in sf["diagnosis"]["surgical_margins"]
    assert "0 of 2" in sf["diagnosis"]["lymph_nodes"]
    assert "pT2 pN0" in sf["diagnosis"]["pathologic_stage"]

    # 4. Grounded Summary
    summary = data["summary"]
    assert "Histopathology" in summary
    assert "Invasive Ductal Carcinoma" in summary
    assert "Grade 2" in summary
    assert "Clinical Limitations" in summary
    # Verifies system does NOT invent chemotherapy or medical orders
    assert "prescription" not in summary.lower()


# ==============================================================================
# Case 2: Tumour-Marker Report
# ==============================================================================
def test_tumour_marker_report_extraction(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "CENTRAL ONCOLOGY CLINICAL BIOCHEMISTRY",
        "Serum Tumor Marker Panel",
        "Patient: Synthetic Test Patient 02",
        "Total PSA: 9.4 ng/mL (Reference: 0.0 - 4.0 ng/mL)",
        "Free PSA: 1.2 ng/mL (Reference: 0.0 - 1.0 ng/mL)",
        "CEA: 2.3 ng/mL (Reference: < 3.0 ng/mL)",
        "CA 19-9: 18 U/mL (Reference: < 37.0 U/mL)",
        "CA 125: 12 U/mL (Reference: < 35.0 U/mL)",
        "Notes: Analytical precision validated on automated electrochemiluminescence analyzer."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("tumor_markers.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Prostate & GI Tumor Marker Panel", "report_date": "2026-10-22"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    assert data["report_category"] == ReportCategory.TUMOUR_MARKERS
    assert data["classification_confidence"] == "high"
    assert data["processing_status"] == "Clinically structured"

    sf = data["structured_findings"]
    tm_list = sf["tumor_markers"]
    assert len(tm_list) >= 4

    psa_item = next(tm for tm in tm_list if tm["key"] == "total_psa")
    assert psa_item["value"] == 9.4
    assert psa_item["unit"] == "ng/mL"
    assert psa_item["status"] == "elevated"

    cea_item = next(tm for tm in tm_list if tm["key"] == "cea")
    assert cea_item["value"] == 2.3
    assert cea_item["unit"] == "ng/mL"
    assert cea_item["status"] == "normal"

    # Summary contains explicit tumour marker context & limitations
    summary = data["summary"]
    assert "Elevated marker(s)" in summary
    assert "Total PSA" in summary
    assert "Tumour markers must NEVER be interpreted in isolation" in summary


# ==============================================================================
# Case 3: CBC Report
# ==============================================================================
def test_cbc_report_extraction(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "HEMATOLOGY DIVISION",
        "Complete Blood Count (CBC) with Differential",
        "White Blood Cells: 6.8 x10^3/uL (Reference: 4.0 - 11.0)",
        "Red Blood Cells: 4.6 x10^6/uL (Reference: 4.0 - 5.8)",
        "Hemoglobin: 14.1 g/dL (Reference: 12.0 - 17.5)",
        "Hematocrit: 41.5 % (Reference: 36.0 - 50.0)",
        "Platelet Count: 245 x10^3/uL (Reference: 150 - 450)",
        "Neutrophils: 58 % (Reference: 40 - 75)",
        "Lymphocytes: 32 % (Reference: 20 - 45)"
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("cbc_report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Annual Complete Blood Count", "report_date": "2026-10-25"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    assert data["report_category"] == ReportCategory.CBC_ROUTINE_BLOOD
    assert data["processing_status"] == "Clinically structured"
    sf = data["structured_findings"]
    assert len(sf["laboratory_parameters"]) >= 5

    hgb = next(l for l in sf["laboratory_parameters"] if l["key"] == "hemoglobin")
    assert hgb["value"] == 14.1
    assert hgb["status"] == "normal"


# ==============================================================================
# Case 4: Composite Report (Routine Blood + Other Findings)
# ==============================================================================
def test_composite_report_routine_and_other_findings(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "INTEGRATED CLINICAL SERVICES",
        "Comprehensive Oncology Follow-Up Evaluation",
        "Hematology Panel:",
        "Hemoglobin: 11.2 g/dL (Reference: 12.0 - 17.5)",
        "Fasting Blood Glucose: 105 mg/dL (Reference: 70 - 99)",
        "Heart Rate: 76 bpm",
        "Serum Tumor Markers:",
        "CA 125: 48 U/mL (Reference: < 35.0 U/mL)",
        "CEA: 1.8 ng/mL (Reference: < 3.0 ng/mL)",
        "Impression: Mild microcytic anemia, slightly impaired fasting glucose, and elevated CA 125."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("composite_report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Integrated Blood & Tumor Marker Evaluation", "report_date": "2026-10-26"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    sf = data["structured_findings"]
    # Both routine blood and tumor markers must be captured
    assert len(sf["tumor_markers"]) >= 1
    assert any(tm["key"] == "ca_125" for tm in sf["tumor_markers"])
    assert any(lab["key"] == "hemoglobin" for lab in sf["laboratory_parameters"])

    # Heart Rate captured for Digital Twin sync
    assert len(data["biomarkers"]) > 0
    hr_bio = next(b for b in data["biomarkers"] if b["key"] == "heart_rate")
    assert hr_bio["value"] == 76.0


# ==============================================================================
# Case 5: Scanned PDF Requiring OCR
# ==============================================================================
def test_scanned_pdf_requiring_ocr(test_client, auth_context):
    # A) Without OCR engine: clean diagnostic and status Needs review
    scanned_pdf = generate_synthetic_pdf([])  # Empty digital text stream

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("scanned_document.pdf", scanned_pdf, "application/pdf")},
        data={"title": "Scanned Pathology Sheet", "report_date": "2026-10-24"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]
    assert data["is_scanned"] == True
    assert data["processing_status"] in ["Needs review", "Failed"]
    assert "scanned" in data["summary"].lower()

    # B) With registered OCR engine: recovers text and processes successfully
    def mock_ocr(file_bytes, filename):
        return (
            "SURGICAL PATHOLOGY REPORT\n"
            "Specimen: Left Thyroid Core Biopsy\n"
            "Diagnosis: Papillary Thyroid Carcinoma\n"
            "Histologic Grade: Well differentiated"
        )

    register_ocr_handler(mock_ocr)

    res_ocr = test_client.post(
        "/api/reports/upload",
        files={"file": ("scanned_recovered.pdf", scanned_pdf, "application/pdf")},
        data={"title": "Scanned Pathology Sheet OCR", "report_date": "2026-10-24"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res_ocr.status_code == 201
    data_ocr = res_ocr.json()["report"]
    assert data_ocr["report_category"] == ReportCategory.HISTOPATHOLOGY_BIOPSY
    assert data_ocr["processing_status"] == "Clinically structured"
    assert "Papillary Thyroid Carcinoma" in data_ocr["summary"]


# ==============================================================================
# Case 6: Report with No Recognized Parameters
# ==============================================================================
def test_report_containing_no_recognized_parameters(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "General Medical Consultation Clinical Notes",
        "Patient presented for routine annual wellness conversation.",
        "Reports feeling well with no active complaints or fatigue.",
        "Advised to continue regular physical walking and Mediterranean diet.",
        "Follow up scheduled in 12 months."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("consultation_note.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Annual Consultation Note", "report_date": "2026-10-27"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    assert data["report_category"] in [ReportCategory.OTHER_MEDICAL, ReportCategory.UNCERTAIN]
    # Extraction does NOT falsely claim successful clinical vital structuring
    assert data["processing_status"] in ["Text extracted", "Needs review"]
    assert data["structured_findings"]["tumor_markers"] == []


# ==============================================================================
# Case 7: Unreadable or Malformed PDF
# ==============================================================================
def test_unreadable_or_malformed_pdf(test_client, auth_context):
    # Spoofed non-PDF file
    bad_bytes = b"Not a real PDF file content without magic header."
    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("corrupt.pdf", bad_bytes, "application/pdf")},
        data={"title": "Corrupt File Test", "report_date": "2026-10-27"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 400
    assert "valid PDF header" in res.json()["detail"]


# ==============================================================================
# Case 8: Report with Missing Units or Reference Ranges
# ==============================================================================
def test_report_with_missing_units_or_reference_ranges(test_client, auth_context):
    # Tumor markers reported without units or reference intervals
    pdf_bytes = generate_synthetic_pdf([
        "Tumor Marker Assessment Check",
        "Total PSA: 7.8",
        "CEA: 5.6",
        "Note: Reference ranges unavailable due to analyzer calibration change."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("missing_ranges.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Markers Missing Units", "report_date": "2026-10-27"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    # Values must be extracted accurately, missing values remain missing (never 0 or guessed)
    sf = data["structured_findings"]
    psa = next(tm for tm in sf["tumor_markers"] if tm["key"] == "total_psa")
    assert psa["value"] == 7.8
    assert psa["reference_range"] is None

    # Status reflects incomplete data
    assert data["processing_status"] == "Partially processed"
    assert len(data["processing_warnings"]) > 0
    assert "Missing / Uncertain Data" in data["summary"]


# ==============================================================================
# Case 9: Report with Explicitly Stated Normal or Negative Findings
# ==============================================================================
def test_report_with_negative_findings(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "Surgical Pathology Report",
        "Specimen Received: Right axillary lymph node core biopsy",
        "Microscopic Examination:",
        "Sections show lymphoid tissue with reactive follicular hyperplasia.",
        "Negative for malignancy.",
        "No evidence of metastatic carcinoma or lymphoma.",
        "Flow cytometry: Polyclonal lymphoid population."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("benign_biopsy.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Axillary Node Biopsy Report", "report_date": "2026-10-28"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    assert data["report_category"] == ReportCategory.HISTOPATHOLOGY_BIOPSY
    sf = data["structured_findings"]
    assert sf["diagnosis"]["is_benign_or_negative"] == True
    summary = data["summary"]
    assert "benign/negative findings" in summary
    # Verifies cancer is NOT falsely diagnosed
    assert "Invasive Carcinoma" not in summary


# ==============================================================================
# Case 10: Report Whose Type Cannot Be Classified Confidently
# ==============================================================================
def test_report_type_uncertain(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "Administrative Custody Transfer Notice",
        "Folder: ARCH-992-B",
        "Document pages transferred: 12",
        "Courier receipt: Signed by Clerk 4.",
        "Storage box: Warehouse section 3."
    ])

    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("memo.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Archive Transfer Notice", "report_date": "2026-10-28"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    data = res.json()["report"]

    assert data["report_category"] == ReportCategory.UNCERTAIN
    assert data["classification_confidence"] == "low"
    assert data["processing_status"] == "Needs review"
    assert "Report type uncertain" in data["category_name"]
    assert "requires human review" in data["summary"].lower()


# ==============================================================================
# Case 11: Patient Isolation & Web3 Cryptographic Off-Chain Integrity
# ==============================================================================
def test_patient_isolation_and_web3_cryptographic_integrity(test_client, auth_context):
    pdf_bytes = generate_synthetic_pdf([
        "Serum Tumor Marker Panel",
        "Total PSA: 5.8 ng/mL (Reference: 0.0 - 4.0 ng/mL)",
        "CEA: 2.0 ng/mL (Reference: < 3.0 ng/mL)"
    ])

    # 1. Upload report for Patient Alpha
    res = test_client.post(
        "/api/reports/upload",
        files={"file": ("confidential_report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Patient Alpha Oncology Panel", "report_date": "2026-10-28"},
        headers={"Authorization": f"Bearer {auth_context['token']}"}
    )
    assert res.status_code == 201
    report_id = res.json()["report"]["id"]

    # 2. Cryptographic SHA-256 hash generated and stored
    file_hash = res.json()["report"]["file_hash_sha256"]
    assert file_hash is not None
    assert len(file_hash) == 64  # Valid SHA-256 hex string

    # 3. Create User Beta and Patient Beta
    db = TestingSessionLocal()
    patient_beta = Patient(
        id="PT-BETA",
        name="Bob Beta",
        age=40,
        gender="Male",
        is_synthetic=False
    )
    user_beta = User(
        id="USR-BETA",
        email="beta@intruder.org",
        hashed_password=hash_password("Password123!"),
        full_name="Bob Beta",
        patient_id="PT-BETA"
    )
    db.add_all([patient_beta, user_beta])
    db.commit()
    db.close()
    token_beta = create_access_token({"sub": "USR-BETA", "email": "beta@intruder.org"})

    # 4. User Beta forbidden from accessing Patient Alpha's report (403 Forbidden)
    res_forbidden = test_client.get(
        f"/api/reports/{report_id}",
        headers={"Authorization": f"Bearer {token_beta}"}
    )
    assert res_forbidden.status_code == 403

