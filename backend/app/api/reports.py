import os
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.report import MedicalReport
from app.models.measurement import Measurement
from app.models.twin_state import TwinState
from app.digital_twin.engine import DigitalTwinEngine
from app.services.auth import get_current_user, get_optional_current_user, verify_patient_authorization
from app.services.report_classifier import (
    classify_medical_report,
    ReportCategory,
    CATEGORY_DISPLAY_NAMES
)
from app.services.ocr_service import extract_document_text
from app.services.report_extractor import extract_structured_findings
from app.services.report_summary import generate_grounded_clinical_summary
from app.services.report_parser import (
    parse_clinical_biomarkers,
    search_report_text,
    generate_report_summary
)
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/reports", tags=["Medical Report Upload & Search Engine"])
logger = logging.getLogger("uvicorn.error")

IST_OFFSET = timezone(timedelta(hours=5, minutes=30))


def _format_ist_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Formats an arbitrary UTC or naive datetime into canonical Indian Standard Time string."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ist_dt = dt.astimezone(IST_OFFSET)
    return ist_dt.strftime("%d %b %Y, %I:%M %p IST")

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_dir, "..", "..", ".."))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(_project_root, "uploads", "reports"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class ConfirmBiomarkerPayload(BaseModel):
    key: str = Field(..., description="e.g. 'heart_rate'")
    value: float = Field(..., description="Confirmed numeric value")
    unit: str = Field("bpm", description="e.g. 'bpm'")
    context: str = Field("resting", description="'resting', 'active', 'clinical', etc.")
    observation_timestamp: Optional[datetime] = None
    notes: Optional[str] = None


class UpdateStructuredFindingsPayload(BaseModel):
    structured_findings: Dict[str, Any]
    notes: Optional[str] = None


def validate_file_content(file_bytes: bytes, ext: str) -> str:
    """Verifies file magic signature bytes so extensions alone cannot be spoofed."""
    if ext == ".pdf":
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed file: File extension is .pdf but content does not match a valid PDF header."
            )
        return "pdf"
    elif ext == ".png":
        if not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed file: File extension is .png but content does not match a valid PNG header."
            )
        return "png"
    elif ext in [".jpg", ".jpeg"]:
        if not file_bytes.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed file: File extension is JPEG/JPG but content does not match a valid JPEG header."
            )
        return "jpeg" if ext == ".jpeg" else "jpg"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format '{ext}'.")


def _format_report_dict(r: MedicalReport, search_matches: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper to convert MedicalReport DB model into comprehensive API dictionary."""
    biomarkers = json.loads(r.extracted_vitals) if r.extracted_vitals else []
    structured_findings = json.loads(r.structured_findings) if r.structured_findings else {}
    warnings = json.loads(r.processing_warnings) if r.processing_warnings else []
    evidence = json.loads(r.classification_evidence) if r.classification_evidence else []

    cat_id = r.report_category or ReportCategory.UNCERTAIN
    cat_name = CATEGORY_DISPLAY_NAMES.get(cat_id, "Medical Report")

    is_scanned = bool(
        r.file_type in ["png", "jpg", "jpeg"]
        or not (r.extracted_text and r.extracted_text.strip())
        or "scanned" in (r.extracted_text or "").lower()
        or "no digital text layer" in (r.extracted_text or "").lower()
    )

    return {
        "id": r.id,
        "patient_id": r.patient_id,
        "title": r.title,
        "report_date": r.report_date,
        "file_name": r.file_name,
        "file_type": r.file_type,
        "file_size_bytes": r.file_size_bytes,
        "file_hash_sha256": r.file_hash_sha256,
        "report_category": cat_id,
        "category_name": cat_name,
        "classification_confidence": r.classification_confidence or "low",
        "classification_evidence": evidence,
        "processing_status": r.processing_status or "Uploaded",
        "description": r.description,
        "summary": r.clinical_summary or r.description or "Document uploaded.",
        "clinical_summary": r.clinical_summary,
        "structured_findings": structured_findings,
        "processing_warnings": warnings,
        "extracted_text": r.extracted_text or "",
        "is_scanned": is_scanned,
        "biomarkers": biomarkers,
        "requires_review": (r.processing_status in ["Needs review", "Partially processed", "Failed"] or cat_id == ReportCategory.UNCERTAIN),
        "search_matches": search_matches,
        "created_at": to_utc_iso(r.created_at),
        "upload_timestamp_ist": _format_ist_timestamp(r.created_at),
        "persisted": True,
        "storage_reference": r.file_path
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_medical_report(
    response: Response,
    title: str = Form(..., min_length=1, max_length=256),
    report_date: str = Form(...),
    description: Optional[str] = Form(None),
    patient_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a medical report (PDF or Image), performs content magic-byte validation,
    computes SHA-256 integrity hash, runs multi-category classification,
    extracts category-specific structured clinical parameters, generates grounded summary,
    and links to target patient.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats are: PDF, PNG, JPG, JPEG."
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 25 MB limit."
        )

    # Magic byte validation
    file_type = validate_file_content(file_bytes, ext)

    # Cryptographic off-chain integrity commitment (SHA-256)
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Resolve target patient and user
    target_patient_id = patient_id or (current_user.patient_id if current_user else "PT-DEMO-001")
    target_user_id = current_user.id if current_user else "USR-DEMO"

    # Enforce authorization
    verify_patient_authorization(target_patient_id, current_user, db)

    # Check for duplicate submission for this patient to prevent redundant entries
    existing_report = db.query(MedicalReport).filter(
        MedicalReport.patient_id == target_patient_id,
        MedicalReport.file_hash_sha256 == file_hash
    ).first()
    if existing_report and existing_report.processing_status not in ["Failed", "Needs review"]:
        if response is not None:
            response.status_code = status.HTTP_200_OK
        return {
            "success": True,
            "persisted": True,
            "is_duplicate": True,
            "report_id": existing_report.id,
            "message": f"This report has already been analyzed and saved in this patient's Health Records (Report #{existing_report.id}).",
            "report": _format_report_dict(existing_report)
        }

    # Sanitize and create unique file path
    safe_name = f"{target_user_id}_{int(datetime.now().timestamp())}_{os.path.basename(file.filename)}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 1. Document Extraction & OCR
    doc_res = extract_document_text(file_bytes, file.filename, ext)
    extracted_text = doc_res["text"] or ""
    is_scanned = doc_res["is_scanned"]
    ocr_message = doc_res["ocr_message"]

    # 2. Handle complete extraction failures (encrypted, corrupted, empty)
    if doc_res["error"]:
        report = MedicalReport(
            user_id=target_user_id,
            patient_id=target_patient_id,
            title=title.strip(),
            report_date=report_date.strip(),
            file_name=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size,
            file_hash_sha256=file_hash,
            report_category=ReportCategory.UNCERTAIN,
            classification_confidence="low",
            classification_evidence=json.dumps([f"Extraction failed: {doc_res['error']}"]),
            processing_status="Failed",
            description=description.strip() if description else None,
            extracted_text=extracted_text,
            clinical_summary=(
                f"Document '{title.strip()}' ({report_date.strip()}). Extraction Status: Failed. "
                f"Error: {doc_res['error']} Please review file integrity or upload an unencrypted document."
            ),
            structured_findings=json.dumps({}),
            processing_warnings=json.dumps([doc_res["error"]]),
            extracted_vitals=json.dumps([])
        )
        try:
            db.add(report)
            db.commit()
            db.refresh(report)
        except Exception as db_err:
            db.rollback()
            logger.error(f"Failed to persist failed report record: {db_err}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database persistence failed: {str(db_err)}"
            )
        return {
            "success": True,
            "persisted": True,
            "report_id": report.id,
            "message": f"Document saved with status Failed: {doc_res['error']}",
            "report": _format_report_dict(report)
        }

    # 3. Classify Document
    classification = classify_medical_report(extracted_text, title.strip())
    category_id = classification["category_id"]

    # 4. Extract Category-Specific Structured Findings
    structured = extract_structured_findings(extracted_text, category_id, title.strip())

    # 5. Extract Candidate Biomarkers for physiological twin
    biomarkers = parse_clinical_biomarkers(extracted_text)

    # 6. Determine Processing Status
    # Statuses: 'Uploaded', 'Text extracted', 'Clinically structured', 'Partially processed', 'Needs review', 'Failed'
    warnings = list(structured.get("missing_fields", []))
    if not extracted_text.strip():
        processing_status = "Failed"
        warnings.append("No text could be extracted from this document.")
    elif is_scanned and not doc_res["ocr_applied"]:
        processing_status = "Needs review"
        warnings.append(ocr_message or "Scanned document with unconfigured OCR.")
    elif category_id == ReportCategory.UNCERTAIN:
        processing_status = "Needs review"
        warnings.append("Document classification is uncertain. Requires manual review.")
    elif structured.get("missing_fields"):
        processing_status = "Partially processed"
    elif (structured.get("tumor_markers") or structured.get("diagnosis") or structured.get("ihc_markers")
          or structured.get("molecular_tests") or structured.get("radiology") or structured.get("laboratory_parameters")):
        processing_status = "Clinically structured"
    else:
        processing_status = "Text extracted"

    # 7. Generate Grounded Clinical Summary
    summary = generate_grounded_clinical_summary(
        title=title.strip(),
        report_date=report_date.strip(),
        classification=classification,
        extraction_result=structured,
        raw_text=extracted_text,
        processing_status=processing_status,
        is_scanned=is_scanned,
        ocr_message=ocr_message
    )

    # 8. Save or Update Record in Database
    if existing_report:
        report = existing_report
        report.title = title.strip()
        report.report_date = report_date.strip()
        report.file_name = file.filename
        report.file_path = file_path
        report.file_type = file_type
        report.file_size_bytes = file_size
        report.report_category = category_id
        report.classification_confidence = classification["confidence"]
        report.classification_evidence = json.dumps(classification["evidence"])
        report.processing_status = processing_status
        report.description = description.strip() if description else None
        report.extracted_text = extracted_text
        report.clinical_summary = summary
        report.structured_findings = json.dumps(structured)
        report.processing_warnings = json.dumps(warnings)
        report.extracted_vitals = json.dumps(biomarkers)
    else:
        report = MedicalReport(
            user_id=target_user_id,
            patient_id=target_patient_id,
            title=title.strip(),
            report_date=report_date.strip(),
            file_name=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size_bytes=file_size,
            file_hash_sha256=file_hash,
            report_category=category_id,
            classification_confidence=classification["confidence"],
            classification_evidence=json.dumps(classification["evidence"]),
            processing_status=processing_status,
            description=description.strip() if description else None,
            extracted_text=extracted_text,
            clinical_summary=summary,
            structured_findings=json.dumps(structured),
            processing_warnings=json.dumps(warnings),
            extracted_vitals=json.dumps(biomarkers)
        )
        db.add(report)

    try:
        db.commit()
        db.refresh(report)
    except Exception as db_err:
        db.rollback()
        logger.error(f"Failed to persist processed medical report: {db_err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report processing succeeded, but database persistence failed: {str(db_err)}. You may retry saving."
        )

    return {
        "success": True,
        "persisted": True,
        "is_duplicate": False,
        "report_id": report.id,
        "message": f"Medical report uploaded, analyzed, and permanently saved. Status: {processing_status}.",
        "report": _format_report_dict(report)
    }


@router.get("", include_in_schema=True)
@router.get("/", include_in_schema=False)
def list_user_reports(
    patient_id: Optional[str] = Query(None, description="Filter reports for specific patient"),
    category: Optional[str] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search keyword across titles, descriptions, and extracted text"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Lists medical reports for the selected patient or authenticated user with search and category filtering."""
    try:
        if patient_id:
            verify_patient_authorization(patient_id, current_user, db)
            query = db.query(MedicalReport).filter(MedicalReport.patient_id == patient_id)
        elif current_user:
            query = db.query(MedicalReport).filter(MedicalReport.user_id == current_user.id)
        else:
            # Default demo patient
            query = db.query(MedicalReport).filter(MedicalReport.patient_id == "PT-DEMO-001")

        if category and category != "ALL":
            query = query.filter(MedicalReport.report_category == category)
        if start_date:
            query = query.filter(MedicalReport.report_date >= start_date)
        if end_date:
            query = query.filter(MedicalReport.report_date <= end_date)

        # Order by newest upload first, then clinical report date
        reports = query.order_by(MedicalReport.created_at.desc(), MedicalReport.report_date.desc()).offset(offset).limit(limit).all()

        results = []
        for r in reports:
            search_matches = None
            if search and search.strip():
                q = search.strip().lower()
                in_meta = (
                    (q in r.title.lower())
                    or (r.description and q in r.description.lower())
                    or (r.clinical_summary and q in r.clinical_summary.lower())
                    or (r.structured_findings and q in r.structured_findings.lower())
                    or (r.report_category and q in r.report_category.lower())
                )
                text_search = search_report_text(r.extracted_text or "", search.strip())

                if not in_meta and text_search["matches_found"] == 0:
                    continue
                search_matches = text_search

            results.append(_format_report_dict(r, search_matches=search_matches))

        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying medical reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while retrieving report history: {str(e)}"
        )


@router.get("/{report_id}")
def get_report_details(
    report_id: int,
    search: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full details, extracted text, structured findings, and search matches for a specific report."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    verify_patient_authorization(report.patient_id, current_user, db)
    search_result = search_report_text(report.extracted_text or "", search) if search else None

    return _format_report_dict(report, search_matches=search_result)


@router.post("/{report_id}/reprocess")
def reprocess_medical_report(
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Re-analyzes and re-extracts findings for an existing report."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report or physical file not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    with open(report.file_path, "rb") as f:
        file_bytes = f.read()

    ext = os.path.splitext(report.file_name)[1].lower()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    doc_res = extract_document_text(file_bytes, report.file_name, ext)
    extracted_text = doc_res["text"] or ""
    is_scanned = doc_res["is_scanned"]
    ocr_message = doc_res["ocr_message"]

    classification = classify_medical_report(extracted_text, report.title)
    category_id = classification["category_id"]
    structured = extract_structured_findings(extracted_text, category_id, report.title)
    biomarkers = parse_clinical_biomarkers(extracted_text)

    warnings = list(structured.get("missing_fields", []))
    if not extracted_text.strip():
        processing_status = "Failed"
        warnings.append("No text could be extracted.")
    elif is_scanned and not doc_res["ocr_applied"]:
        processing_status = "Needs review"
    elif category_id == ReportCategory.UNCERTAIN:
        processing_status = "Needs review"
    elif structured.get("missing_fields"):
        processing_status = "Partially processed"
    elif (structured.get("tumor_markers") or structured.get("diagnosis") or structured.get("ihc_markers")
          or structured.get("molecular_tests") or structured.get("radiology") or structured.get("laboratory_parameters")):
        processing_status = "Clinically structured"
    else:
        processing_status = "Text extracted"

    summary = generate_grounded_clinical_summary(
        title=report.title,
        report_date=report.report_date,
        classification=classification,
        extraction_result=structured,
        raw_text=extracted_text,
        processing_status=processing_status,
        is_scanned=is_scanned,
        ocr_message=ocr_message
    )

    report.file_hash_sha256 = file_hash
    report.report_category = category_id
    report.classification_confidence = classification["confidence"]
    report.classification_evidence = json.dumps(classification["evidence"])
    report.processing_status = processing_status
    report.extracted_text = extracted_text
    report.clinical_summary = summary
    report.structured_findings = json.dumps(structured)
    report.processing_warnings = json.dumps(warnings)
    report.extracted_vitals = json.dumps(biomarkers)

    db.commit()
    db.refresh(report)

    return {
        "success": True,
        "message": f"Report reprocessed. Status: {processing_status}.",
        "report": _format_report_dict(report)
    }


@router.put("/{report_id}/structured-findings")
def update_report_structured_findings(
    report_id: int,
    payload: UpdateStructuredFindingsPayload,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Allows patient or clinician review to update structured findings."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    report.structured_findings = json.dumps(payload.structured_findings)
    if payload.notes:
        report.description = f"{report.description or ''}\n[Review Note]: {payload.notes}".strip()
    db.commit()
    db.refresh(report)

    return {
        "success": True,
        "message": "Structured findings updated successfully.",
        "report": _format_report_dict(report)
    }


@router.get("/{report_id}/verify-integrity")
def verify_report_integrity(
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Cryptographically verifies the stored report file against its recorded off-chain SHA-256 integrity hash.
    Proves that the persisted document has not been altered, tampered with, or corrupted.
    """
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    if not os.path.exists(report.file_path):
        return {
            "report_id": report.id,
            "patient_id": report.patient_id,
            "title": report.title,
            "file_name": report.file_name,
            "file_exists": False,
            "file_size_bytes": 0,
            "stored_sha256": report.file_hash_sha256,
            "recomputed_sha256": None,
            "is_tamper_free": False,
            "verification_status": "File missing on storage server",
            "verified_at": datetime.now(timezone.utc).isoformat()
        }

    try:
        with open(report.file_path, "rb") as f:
            current_bytes = f.read()
        recomputed_hash = hashlib.sha256(current_bytes).hexdigest()
        is_valid = bool(report.file_hash_sha256 and report.file_hash_sha256.lower() == recomputed_hash.lower())

        return {
            "report_id": report.id,
            "patient_id": report.patient_id,
            "title": report.title,
            "file_name": report.file_name,
            "file_exists": True,
            "file_size_bytes": len(current_bytes),
            "stored_sha256": report.file_hash_sha256,
            "recomputed_sha256": recomputed_hash,
            "is_tamper_free": is_valid,
            "verification_status": "Cryptographically verified: SHA-256 match" if is_valid else "Tamper warning: Hash mismatch",
            "verified_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Integrity verification error for report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify report integrity: {str(e)}"
        )


@router.get("/{report_id}/download")
def download_report_file(
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Securely serves the authorized patient's original uploaded document."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    media_type = "application/pdf" if report.file_type == "pdf" else f"image/{report.file_type}"
    return FileResponse(
        path=report.file_path,
        media_type=media_type,
        filename=report.file_name
    )


@router.delete("/{report_id}")
def delete_medical_report(
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a medical report record and removes its physical file from storage."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    if os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except Exception:
            pass

    db.delete(report)
    db.commit()
    return {"success": True, "message": "Report deleted successfully."}


@router.post("/{report_id}/confirm-biomarkers")
def confirm_report_biomarkers_to_twin(
    report_id: int,
    payload: ConfirmBiomarkerPayload,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Patient Review-and-Confirm step:
    Allows user to review, confirm, or adjust extracted biomarker values before
    they are formally ingested into their canonical health state and digital twin.
    """
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    if payload.key != "heart_rate":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Biomarker '{payload.key}' confirmation is not currently supported in the physiological twin model. Supported: 'heart_rate'."
        )

    if not (30.0 <= payload.value <= 250.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Heart rate value {payload.value} bpm is outside physiological plausibility (30 - 250 bpm)."
        )

    obs_ts = payload.observation_timestamp or datetime.now(timezone.utc)
    if obs_ts.tzinfo is None:
        obs_ts = obs_ts.replace(tzinfo=timezone.utc)

    # Ingest measurement into report.patient_id
    meas = Measurement(
        patient_id=report.patient_id,
        timestamp=obs_ts,
        measurement_type="heart_rate",
        value=float(payload.value),
        unit=payload.unit or "bpm",
        source=f"report_confirmed:{report.id}:{report.file_name}",
        context=payload.context or "resting",
        data_quality="valid",
        is_late_arrival=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(meas)
    db.commit()
    db.refresh(meas)

    # Advance digital twin state
    active_state = db.query(TwinState).filter(
        TwinState.patient_id == report.patient_id,
        TwinState.is_active_version == True
    ).first()

    if not active_state:
        updated_state = DigitalTwinEngine.initialize_twin(patient_id=report.patient_id, db=db)
        stale_count = 0
    else:
        updated_state, stale_count = DigitalTwinEngine.update_twin_with_measurement(
            patient_id=report.patient_id,
            measurement=meas,
            db=db
        )

    return {
        "success": True,
        "message": f"Biomarker confirmed. Digital Twin updated to State Version {updated_state.state_version}.",
        "measurement": {
            "id": meas.id,
            "value": meas.value,
            "unit": meas.unit,
            "timestamp": to_utc_iso(meas.timestamp),
            "context": meas.context
        },
        "digital_twin_update": {
            "current_state_version": updated_state.state_version,
            "latest_heart_rate": updated_state.latest_heart_rate,
            "vital_status": updated_state.vital_status,
            "attestation_status": updated_state.attestation_status,
            "on_chain_tx_hash": updated_state.on_chain_tx_hash,
            "stale_forecasts_invalidated": stale_count
        }
    }


@router.post("/{report_id}/sync-twin")
def sync_report_vitals_to_twin(
    report_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Direct sync of recognized biomarkers to twin (auto-confirm fallback)."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    verify_patient_authorization(report.patient_id, current_user, db)

    biomarkers = json.loads(report.extracted_vitals) if report.extracted_vitals else []
    hr_biomarker = next((b for b in biomarkers if b.get("key") == "heart_rate"), None)

    if not hr_biomarker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No heart rate biomarker detected in this document to sync."
        )

    payload = ConfirmBiomarkerPayload(
        key="heart_rate",
        value=float(hr_biomarker["value"]),
        unit=hr_biomarker.get("unit", "bpm"),
        context="resting"
    )
    return confirm_report_biomarkers_to_twin(report_id, payload, current_user, db)

