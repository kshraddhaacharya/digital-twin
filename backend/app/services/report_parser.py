"""
Medical Report Processing Pipeline for Sovereign Health Twin.
Integrates text extraction, OCR, multi-category classification, structured clinical
extraction, and grounded summary generation.
"""

import io
import re
import json
from typing import Dict, Any, List, Optional

from app.services.report_classifier import (
    classify_medical_report,
    ReportCategory,
    CATEGORY_DISPLAY_NAMES
)
from app.services.ocr_service import (
    extract_document_text,
    register_ocr_handler,
    get_ocr_handler,
    is_tesseract_available
)
from app.services.report_extractor import (
    extract_structured_findings,
    extract_tumor_markers,
    extract_histopathology,
    extract_immunohistochemistry,
    extract_molecular_genetics,
    extract_radiology,
    extract_cbc_analytes,
    extract_biochemistry_analytes,
    find_source_snippet
)
from app.services.report_summary import generate_grounded_clinical_summary


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text from PDF document using enhanced extraction and error handling."""
    res = extract_document_text(pdf_bytes, "document.pdf", ".pdf")
    if res["error"]:
        return f"[PDF parsing warning: {res['error']}]"
    if res["is_scanned"] and not res["ocr_applied"]:
        return (
            "[PDF uploaded successfully, but no digital text layer was found. "
            "This appears to be a scanned image-based document. "
            f"{res['ocr_message'] or 'Please review the document directly or enter key findings manually.'}]"
        )
    return res["text"] or "[Empty document]"


def extract_text_from_image(img_bytes: bytes, filename: str) -> str:
    """Validates image file and extracts text via OCR when available."""
    ext = ".png" if filename.lower().endswith(".png") else ".jpg"
    res = extract_document_text(img_bytes, filename, ext)
    return res["text"]


def parse_clinical_biomarkers(text: str) -> List[Dict[str, Any]]:
    """
    Scans clinical text for standard medical biomarkers, vitals, and tumor markers.
    Labels items with requires_confirmation=True for patient safety before twin sync.
    Does NOT invent values for missing parameters.
    """
    biomarkers = []

    # 1. Heart Rate / Pulse
    hr_match = re.search(r'(?:Heart Rate|Pulse Rate|Pulse|HR)[\s:]+(\d{2,3}(?:\.\d+)?)\s*(?:bpm|BPM|beats\/min)?', text, re.IGNORECASE)
    if hr_match:
        val = float(hr_match.group(1))
        if 30.0 <= val <= 250.0:
            biomarkers.append({
                "name": "Heart Rate",
                "key": "heart_rate",
                "value": val,
                "unit": "bpm",
                "reference_range": "60 - 100 bpm",
                "status": "normal" if 60 <= val <= 100 else ("elevated" if val > 100 else "low"),
                "confidence": "high",
                "requires_confirmation": True
            })

    # 2. Blood Pressure (Systolic / Diastolic)
    bp_match = re.search(r'(?:Blood Pressure|BP)[\s:]+(\d{2,3})\s*[\/|\\]\s*(\d{2,3})\s*(?:mmHg)?', text, re.IGNORECASE)
    if bp_match:
        sys_val = int(bp_match.group(1))
        dia_val = int(bp_match.group(2))
        biomarkers.append({
            "name": "Blood Pressure",
            "key": "blood_pressure",
            "value": f"{sys_val}/{dia_val}",
            "unit": "mmHg",
            "reference_range": "< 120/80 mmHg",
            "status": "normal" if (sys_val <= 120 and dia_val <= 80) else "elevated",
            "confidence": "high",
            "requires_confirmation": True
        })

    # 3. Blood Glucose
    glucose_match = re.search(r'(?:Fasting Blood Sugar|Blood Glucose|Fasting Glucose|Glucose)[\s:]+(\d{2,3}(?:\.\d+)?)\s*(?:mg\/dL|mg\/dl)?', text, re.IGNORECASE)
    if glucose_match:
        val = float(glucose_match.group(1))
        biomarkers.append({
            "name": "Fasting Glucose",
            "key": "glucose",
            "value": val,
            "unit": "mg/dL",
            "reference_range": "70 - 99 mg/dL",
            "status": "normal" if 70 <= val <= 99 else ("elevated" if val > 99 else "low"),
            "confidence": "high",
            "requires_confirmation": True
        })

    # 4. Total Cholesterol
    chol_match = re.search(r'(?:Total Cholesterol|Cholesterol)[\s:]+(\d{2,3}(?:\.\d+)?)\s*(?:mg\/dL|mg\/dl)?', text, re.IGNORECASE)
    if chol_match:
        val = float(chol_match.group(1))
        biomarkers.append({
            "name": "Total Cholesterol",
            "key": "total_cholesterol",
            "value": val,
            "unit": "mg/dL",
            "reference_range": "< 200 mg/dL",
            "status": "normal" if val < 200 else "elevated",
            "confidence": "moderate",
            "requires_confirmation": True
        })

    # 5. Oxygen Saturation (SpO2)
    spo2_match = re.search(r'(?:SpO2|Oxygen Saturation|O2 Sat)[\s:]+(\d{2,3}(?:\.\d+)?)\s*(?:%)?', text, re.IGNORECASE)
    if spo2_match:
        val = float(spo2_match.group(1))
        if val <= 100.0:
            biomarkers.append({
                "name": "Oxygen Saturation (SpO2)",
                "key": "spo2",
                "value": val,
                "unit": "%",
                "reference_range": "95 - 100 %",
                "status": "normal" if val >= 95 else "low",
                "confidence": "high",
                "requires_confirmation": True
            })

    # 6. Hemoglobin
    hgb_match = re.search(r'(?:Hemoglobin|Hgb)[\s:]+(\d{1,2}(?:\.\d+)?)\s*(?:g\/dL|g\/dl)?', text, re.IGNORECASE)
    if hgb_match:
        val = float(hgb_match.group(1))
        biomarkers.append({
            "name": "Hemoglobin",
            "key": "hemoglobin",
            "value": val,
            "unit": "g/dL",
            "reference_range": "12.0 - 17.5 g/dL",
            "status": "normal" if 12.0 <= val <= 17.5 else ("elevated" if val > 17.5 else "low"),
            "confidence": "moderate",
            "requires_confirmation": True
        })

    # 7. Tumor Markers as candidate parameters
    tm_list = extract_tumor_markers(text)
    for tm in tm_list:
        biomarkers.append({
            "name": tm["name"],
            "key": tm["key"],
            "value": tm["value"],
            "unit": tm.get("unit") or "",
            "reference_range": tm.get("reference_range") or "Unspecified",
            "status": tm.get("status") or "reported",
            "confidence": tm.get("confidence", "moderate"),
            "requires_confirmation": False
        })

    return biomarkers


def generate_report_summary(
    title: str,
    report_date: str,
    extracted_text: str,
    biomarkers: List[Dict[str, Any]],
    file_type: str = "pdf"
) -> str:
    """
    Constructs a factual, transparent clinical summary from parsed document text.
    Classifies the report dynamically instead of forcing every report into cardiovascular vitals.
    """
    text_clean = (extracted_text or "").strip()
    is_scanned = (
        not text_clean
        or "no digital text layer was found" in text_clean
        or "Automated OCR is not" in text_clean
        or "Could not read text" in text_clean
    )

    classification = classify_medical_report(text_clean, title)
    findings = extract_structured_findings(text_clean, classification["category_id"], title)

    # Determine processing status
    if not text_clean:
        status = "Failed"
    elif is_scanned:
        status = "Needs review"
    elif classification["category_id"] == ReportCategory.UNCERTAIN:
        status = "Needs review"
    elif findings["missing_fields"]:
        status = "Partially processed"
    elif (findings["tumor_markers"] or findings["diagnosis"] or findings["ihc_markers"]
          or findings["molecular_tests"] or findings["radiology"] or findings["laboratory_parameters"]):
        status = "Clinically structured"
    else:
        status = "Text extracted"

    return generate_grounded_clinical_summary(
        title=title,
        report_date=report_date,
        classification=classification,
        extraction_result=findings,
        raw_text=text_clean,
        processing_status=status,
        is_scanned=is_scanned
    )


def search_report_text(full_text: str, query: str) -> Dict[str, Any]:
    """Search engine scanning report text for keywords, returning matching snippets and line numbers."""
    if not full_text or not query:
        return {"query": query, "matches_found": 0, "snippets": []}

    q = query.strip().lower()
    lines = full_text.splitlines()
    matches = []

    for idx, line in enumerate(lines):
        if q in line.lower():
            start_ctx = max(0, idx - 1)
            end_ctx = min(len(lines), idx + 2)
            snippet = "\n".join(lines[start_ctx:end_ctx])
            matches.append({
                "line_number": idx + 1,
                "matched_line": line.strip(),
                "snippet": snippet
            })

    return {
        "query": query,
        "matches_found": len(matches),
        "snippets": matches
    }

