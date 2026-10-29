"""
Clinical Summary Generator for Sovereign Health Twin.
Generates objective, transparent clinical summaries strictly grounded in document text
and structured extraction results. Distinguishes what is stated, what was extracted,
what is missing/uncertain, and explicitly recommends clinician evaluation without
fabricating cancer diagnoses, staging, or therapeutic advice.
"""

from typing import Dict, Any, List
from app.services.report_classifier import ReportCategory, CATEGORY_DISPLAY_NAMES


def generate_grounded_clinical_summary(
    title: str,
    report_date: str,
    classification: Dict[str, Any],
    extraction_result: Dict[str, Any],
    raw_text: str,
    processing_status: str,
    is_scanned: bool = False,
    ocr_message: str = None
) -> str:
    """
    Constructs a 5-point grounded clinical summary:
    1. Detected report type & extraction status.
    2. Key findings explicitly present.
    3. Extracted results with units and reference ranges.
    4. Important missing or unreadable information.
    5. Relevant clinical limitations and clinician review recommendation.
    """
    category_id = classification.get("category_id", ReportCategory.UNCERTAIN)
    category_name = classification.get("category_name", CATEGORY_DISPLAY_NAMES.get(category_id, "Medical Report"))
    confidence = classification.get("confidence", "low").capitalize()

    # Handle unreadable/scanned document failure
    if not raw_text or not raw_text.strip() or processing_status == "Failed":
        return (
            f"Document '{title}' ({report_date}). Extraction Status: Failed. "
            "No extractable digital text could be recovered from this document. "
            f"{ocr_message or 'The file may be corrupted, empty, or password-protected.'} "
            "Automated clinical structuring cannot proceed. Please inspect the original file directly."
        )

    if is_scanned and "No embedded digital character layer" in (ocr_message or ""):
        return (
            f"Document '{title}' ({report_date}). Extraction Status: Needs review. "
            "The document was uploaded as a scanned or image-based document without an embedded digital text layer. "
            "Automated OCR is not configured on this host; text and biomarkers could not be parsed automatically. "
            "Important note: Please review the original document manually or enter vital readings directly."
        )

    sections = []

    # 1. Report Type & Extraction Status
    sections.append(
        f"1. Document Overview: '{title}' (Report Date: {report_date}). "
        f"Detected Category: {category_name} ({confidence} classification confidence). "
        f"Extraction Status: {processing_status}."
    )

    # 2. Key Explicit Findings
    findings_str = []
    if category_id == ReportCategory.TUMOUR_MARKERS:
        tms = extraction_result.get("tumor_markers", [])
        if tms:
            elevated = [f"{tm['name']} ({tm['value']} {tm.get('unit') or ''})" for tm in tms if tm.get("status") == "elevated"]
            normal = [f"{tm['name']} ({tm['value']} {tm.get('unit') or ''})" for tm in tms if tm.get("status") == "normal"]
            if elevated:
                findings_str.append(f"Elevated marker(s) relative to reference thresholds: {', '.join(elevated)}.")
            if normal:
                findings_str.append(f"Marker(s) within standard reference limits: {', '.join(normal)}.")
        else:
            findings_str.append("No specific tumor marker quantitative values could be confirmed in text.")

    elif category_id in [ReportCategory.HISTOPATHOLOGY_BIOPSY, ReportCategory.IMMUNOHISTOCHEMISTRY]:
        hp = extraction_result.get("diagnosis") or {}
        if hp.get("is_benign_or_negative"):
            findings_str.append("The report explicitly documents benign/negative findings with no evidence of malignancy.")
        elif hp.get("stated_diagnosis"):
            findings_str.append(f"Stated Histopathologic Diagnosis: \"{hp['stated_diagnosis']}\".")
        
        if hp.get("specimen_site"):
            findings_str.append(f"Specimen/Site: {hp['specimen_site']}.")
        if hp.get("tumor_grade"):
            findings_str.append(f"Histologic Grade: {hp['tumor_grade']}.")
        if hp.get("surgical_margins"):
            findings_str.append(f"Margins: {hp['surgical_margins']}.")
        if hp.get("lymph_nodes"):
            findings_str.append(f"Lymph Nodes: {hp['lymph_nodes']}.")
        if hp.get("pathologic_stage"):
            findings_str.append(f"Documented Pathologic Stage: {hp['pathologic_stage']}.")

        # Add IHC findings if present
        ihc = extraction_result.get("ihc_markers", [])
        if ihc:
            ihc_summary = "; ".join([f"{item['marker']}: {item['result']}" for item in ihc])
            findings_str.append(f"Immunohistochemical Profile: {ihc_summary}.")

    elif category_id == ReportCategory.MOLECULAR_GENETICS:
        mol = extraction_result.get("molecular_tests", [])
        if mol:
            mol_items = [f"{m['gene']}: {m['alteration']} ({m['clinical_significance']})" for m in mol]
            findings_str.append(f"Genomic Findings: {'; '.join(mol_items)}.")
        else:
            findings_str.append("No specific gene mutations or genomic alterations were identified in the text.")

    elif category_id == ReportCategory.RADIOLOGY_IMAGING:
        rad = extraction_result.get("radiology") or {}
        if rad.get("modality"):
            findings_str.append(f"Imaging Modality: {rad['modality']}.")
        if rad.get("impression"):
            findings_str.append(f"Radiologist Stated Impression: \"{rad['impression']}\".")
        if rad.get("classification"):
            findings_str.append(f"Standard Classification: {rad['classification']}.")
        if rad.get("observations"):
            obs_list = [f"{o['region']}: {o['observation']}" for o in rad["observations"][:3]]
            findings_str.append(f"Key Anatomical Findings: {'; '.join(obs_list)}.")

    elif category_id in [ReportCategory.CBC_ROUTINE_BLOOD, ReportCategory.BIOCHEMISTRY_METABOLIC]:
        labs = extraction_result.get("laboratory_parameters", [])
        if labs:
            abnormal = [f"{lab['name']} ({lab['value']} {lab.get('unit') or ''}, {lab['status']})" for lab in labs if lab.get("status") in ["elevated", "low"]]
            normal_count = sum(1 for lab in labs if lab.get("status") == "normal")
            if abnormal:
                findings_str.append(f"Out-of-range parameter(s): {', '.join(abnormal)}.")
            findings_str.append(f"{normal_count} parameter(s) within standard physiological reference ranges.")
        else:
            findings_str.append("No standard laboratory parameters could be mapped from the document text.")

    elif category_id == ReportCategory.UNCERTAIN:
        findings_str.append("The document structure does not align with standard oncology or clinical laboratory formats. Content requires human review.")
    else:
        cn = extraction_result.get("consultation_notes")
        if cn:
            notes_parts = []
            if cn.get("purpose"):
                notes_parts.append(f"Purpose: \"{cn['purpose']}\".")
            if cn.get("context"):
                notes_parts.append(f"Clinical Context: {cn['context']}")
            if cn.get("assessment"):
                notes_parts.append(f"Assessment: {cn['assessment']}")
            if cn.get("next_steps"):
                notes_parts.append(f"Recommended Next Steps: {cn['next_steps']}")
            findings_str.append(" ".join(notes_parts))
        else:
            findings_str.append("General clinical documentation detected.")

    if findings_str:
        sections.append(f"2. Explicit Clinical Findings: {' '.join(findings_str)}")

    # 3. Extracted Results with Units & Ranges
    results_list = []
    # Include tumor markers
    for tm in extraction_result.get("tumor_markers", []):
        unit_str = f" {tm['unit']}" if tm.get("unit") else " [unit unstated]"
        ref_str = f", ref: {tm['reference_range']}" if tm.get("reference_range") else ", ref: not stated"
        results_list.append(f"{tm['name']}: {tm['value']}{unit_str} ({tm.get('status', 'reported')}{ref_str})")

    # Include laboratory parameters
    for lab in extraction_result.get("laboratory_parameters", []):
        unit_str = f" {lab['unit']}" if lab.get("unit") else ""
        ref_str = f", ref: {lab['reference_range']}" if lab.get("reference_range") else ""
        results_list.append(f"{lab['name']}: {lab['value']}{unit_str} ({lab.get('status', 'normal')}{ref_str})")

    if results_list:
        sections.append(f"3. Structured Numerical & Quantitative Results ({len(results_list)}): {'; '.join(results_list[:8])}.")

    # 4. Missing, Unreadable, or Uncertain Information
    missing_items = extraction_result.get("missing_fields", [])
    if category_id == ReportCategory.UNCERTAIN:
        missing_items.append("Document classification uncertain: Specific diagnostic category could not be verified.")
    if missing_items:
        sections.append(f"4. Missing / Uncertain Data: {'; '.join(missing_items)}.")
    else:
        sections.append("4. Completeness: Primary clinical parameters for this document type were successfully parsed.")

    # 5. Limitations & Clinician Review Notice
    limitation_notes = [
        "This summary is an automated informational extraction from the uploaded record.",
        "It does NOT provide clinical diagnosis, disease staging, or therapeutic guidance."
    ]
    if category_id == ReportCategory.TUMOUR_MARKERS:
        limitation_notes.append(
            "Tumour markers must NEVER be interpreted in isolation as proof of cancer presence or absence, "
            "as benign inflammation, physiological changes, and assay variations frequently affect values."
        )
    limitation_notes.append("All clinical interpretations must be validated by the patient's physician or oncologist.")

    sections.append(f"5. Clinical Limitations & Action: {' '.join(limitation_notes)}")

    return "\n\n".join(sections)

