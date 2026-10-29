"""
Report-Type-Specific Clinical Extraction Service for Sovereign Health Twin.
Extracts structured parameters, observations, tumor markers, histopathology,
IHC, molecular genetics, and imaging findings grounded strictly in the source text.
Preserves original clinician wording and page/snippet references.
Never fabricates missing values or assumes missing means zero/normal.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from app.services.report_classifier import ReportCategory


def split_text_into_pages(text: str) -> List[Tuple[int, str]]:
    """Splits text into (page_number, page_text) tuples using page headers."""
    pages = []
    current_page = 1
    current_lines = []

    for line in text.splitlines():
        page_match = re.match(r"^---\s*Page\s+(\d+).*?---\s*$", line.strip(), re.IGNORECASE)
        if page_match:
            if current_lines:
                pages.append((current_page, "\n".join(current_lines)))
                current_lines = []
            try:
                current_page = int(page_match.group(1))
            except ValueError:
                current_page += 1
        else:
            current_lines.append(line)

    if current_lines:
        pages.append((current_page, "\n".join(current_lines)))

    return pages if pages else [(1, text)]


def find_source_snippet(text: str, match_str: str, window: int = 1) -> Tuple[int, str]:
    """Finds the page number and context snippet for a matched string."""
    pages = split_text_into_pages(text)
    m_clean = match_str.lower()

    for page_num, page_text in pages:
        lines = page_text.splitlines()
        for idx, line in enumerate(lines):
            if m_clean in line.lower():
                start = max(0, idx - window)
                end = min(len(lines), idx + window + 1)
                snippet = " ".join([l.strip() for l in lines[start:end] if l.strip()])
                return page_num, snippet

    return 1, match_str


# ==============================================================================
# 1. Tumour Markers Extractor
# ==============================================================================
VALID_UNITS_REGEX = r"(?:ng\/mL|ng\/ml|ug\/L|ug\/l|U\/mL|U\/ml|mIU\/mL|mIU\/ml|IU\/mL|IU\/ml|mg\/L|mg\/l|mcg\/L)"
REF_RANGE_REGEX = r"(?:[\(\[]\s*(?:ref|reference|normal)?[\s:]*([<>]?\s*[\d\.\s\-–to]+(?:\s*[a-zA-Z\/]+)?)\s*[\)\]]|(?:ref|reference|normal)[\s:]+([<>]?\s*[\d\.\s\-–to]+(?:\s*[a-zA-Z\/]+)?))"

TUMOR_MARKER_PATTERNS = [
    {
        "name": "Total PSA",
        "key": "total_psa",
        "label_regex": r"(?:Total\s+PSA|Prostate\s+Specific\s+Antigen|PSA(?:\s+Total)?)",
        "default_unit": "ng/mL",
        "standard_ref": "0.0 - 4.0 ng/mL",
        "norm_upper": 4.0
    },
    {
        "name": "Free PSA",
        "key": "free_psa",
        "label_regex": r"(?:Free\s+PSA|PSA\s+Free)",
        "default_unit": "ng/mL",
        "standard_ref": "0.0 - 1.0 ng/mL",
        "norm_upper": 1.0
    },
    {
        "name": "CEA (Carcinoembryonic Antigen)",
        "key": "cea",
        "label_regex": r"(?:CEA|Carcinoembryonic\s+Antigen)",
        "default_unit": "ng/mL",
        "standard_ref": "< 3.0 ng/mL",
        "norm_upper": 3.0
    },
    {
        "name": "CA 125 (Ovarian / Peritoneal)",
        "key": "ca_125",
        "label_regex": r"(?:CA[\s-]?125|Cancer\s+Antigen\s+125)",
        "default_unit": "U/mL",
        "standard_ref": "< 35.0 U/mL",
        "norm_upper": 35.0
    },
    {
        "name": "CA 19-9 (Gastrointestinal / Pancreatic)",
        "key": "ca_19_9",
        "label_regex": r"(?:CA[\s-]?19[\s-]?9|Carbohydrate\s+Antigen\s+19[\s-]?9)",
        "default_unit": "U/mL",
        "standard_ref": "< 37.0 U/mL",
        "norm_upper": 37.0
    },
    {
        "name": "CA 15-3 (Breast)",
        "key": "ca_15_3",
        "label_regex": r"(?:CA[\s-]?15[\s-]?3|Cancer\s+Antigen\s+15[\s-]?3)",
        "default_unit": "U/mL",
        "standard_ref": "< 30.0 U/mL",
        "norm_upper": 30.0
    },
    {
        "name": "AFP (Alpha-Fetoprotein)",
        "key": "afp",
        "label_regex": r"(?:AFP|Alpha[\s-]Fetoprotein)",
        "default_unit": "ng/mL",
        "standard_ref": "< 10.0 ng/mL",
        "norm_upper": 10.0
    },
    {
        "name": "Beta-hCG",
        "key": "beta_hcg",
        "label_regex": r"(?:Beta[\s-]hCG|b-hCG|Total\s+beta[\s-]hCG)",
        "default_unit": "mIU/mL",
        "standard_ref": "< 5.0 mIU/mL",
        "norm_upper": 5.0
    },
    {
        "name": "Chromogranin A",
        "key": "chromogranin_a",
        "label_regex": r"Chromogranin\s+A",
        "default_unit": "ng/mL",
        "standard_ref": "< 100 ng/mL",
        "norm_upper": 100.0
    },
]


def extract_tumor_markers(text: str) -> List[Dict[str, Any]]:
    """Extracts tumor markers with strictly preserved numbers, units, ranges, and snippets."""
    results = []

    for tm in TUMOR_MARKER_PATTERNS:
        # Construct targeted regex (allows optional parenthesized abbreviations like '(Total PSA):')
        pattern = rf"{tm['label_regex']}(?:\s*\([^\)]*\))?[\s:]+([<>]?\s*\d+(?:\.\d+)?)(?:\s*({VALID_UNITS_REGEX}))?(?:\s*{REF_RANGE_REGEX})?"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_val_str = match.group(1).strip()
            raw_unit = match.group(2).strip() if match.group(2) else None
            raw_ref = match.group(3) or match.group(4)
            if raw_ref:
                raw_ref = raw_ref.strip()

            val_clean = raw_val_str.replace("<", "").replace(">", "").strip()
            try:
                numeric_val = float(val_clean)
            except ValueError:
                numeric_val = raw_val_str

            status = "reported"
            if isinstance(numeric_val, (int, float)) and tm["norm_upper"] is not None:
                status = "elevated" if numeric_val > tm["norm_upper"] else "normal"

            page_num, snippet = find_source_snippet(text, raw_val_str)

            results.append({
                "name": tm["name"],
                "key": tm["key"],
                "value": numeric_val,
                "unit": raw_unit,
                "reference_range": raw_ref,
                "status": status,
                "snippet": snippet,
                "page_number": page_num,
                "confidence": "high" if raw_unit else "moderate"
            })

    return results


# ==============================================================================
# 2. Histopathology and Biopsy Extractor
# ==============================================================================
def extract_histopathology(text: str) -> Dict[str, Any]:
    """Extracts surgical pathology / biopsy parameters preserving exact clinical phrasing."""
    findings: Dict[str, Any] = {
        "specimen_site": None,
        "procedure": None,
        "stated_diagnosis": None,
        "histologic_type": None,
        "tumor_grade": None,
        "surgical_margins": None,
        "lymph_nodes": None,
        "lymphovascular_invasion": None,
        "perineural_invasion": None,
        "pathologic_stage": None,
        "is_malignant": False,
        "is_benign_or_negative": False,
        "page_number": 1,
        "source_snippet": None
    }

    # Specimen / Site
    specimen_match = re.search(r"(?:Specimen(?:\s+Received|\s+Type)?|Site|Tissue|Clinical\s+Details?)[\s:]+([^\n\.;]+)", text, re.IGNORECASE)
    if specimen_match:
        findings["specimen_site"] = specimen_match.group(1).strip()

    # Histologic Type
    hist_type_match = re.search(r"\b(Invasive\s+Ductal\s+Carcinoma|Invasive\s+Lobular\s+Carcinoma|Adenocarcinoma|Squamous\s+Cell\s+Carcinoma|Tubular\s+Adenoma|Urothelial\s+Carcinoma|Gastrointestinal\s+Stromal\s+Tumor|Follicular\s+Lymphoma|Malignant\s+Melanoma|Papillary\s+Thyroid\s+Carcinoma)\b", text, re.IGNORECASE)
    if hist_type_match:
        findings["histologic_type"] = hist_type_match.group(0).strip()
        findings["is_malignant"] = True

    # Benign / Negative findings check
    benign_match = re.search(r"(?:No\s+(?:evidence\s+of\s+)?malignancy|Benign\s+(?:tissue|lesion|changes?|hyperplasia)|Negative\s+for\s+malignancy|Reactive\s+(?:follicular\s+)?hyperplasia)", text, re.IGNORECASE)
    if benign_match:
        findings["is_benign_or_negative"] = True
        findings["stated_diagnosis"] = benign_match.group(0).strip()

    # Diagnosis / Microscopic Impression
    matches = list(re.finditer(
        r"(?:Histopathologic(?:al)?\s+Diagnosis|Microscopic\s+Diagnosis|Microscopic\s+Examination|(?:FINAL\s+)?DIAGNOSIS|IMPRESSION)[\s:]*\n?\s*([^\n]+(?:\n(?!\s*(?:Gross|Comment|Note|IHC|Pathologic\s+Stage|Clinical|\w+[\s\w]*:))[^\n]+)*)",
        text,
        re.IGNORECASE
    ))
    selected_diag = None
    for m in matches:
        raw_cand = m.group(1).strip()
        cleaned_cand = " ".join([l.strip() for l in raw_cand.splitlines() if l.strip()])
        cleaned_cand = re.split(r",\s*(?:Nottingham|Histologic\s+Grade|Surgical\s+Margins?|Grade)\s*:", cleaned_cand)[0].strip()
        # Ensure it's not a header line like 'Patient: ...' or 'Date: ...'
        if not re.match(r"^(?:Patient|Age|Date|Dr\.|Specimen|MRN|DOB|Sex|Gender)[\s:]", cleaned_cand, re.IGNORECASE):
            selected_diag = cleaned_cand
            break

    if selected_diag:
        findings["stated_diagnosis"] = selected_diag
        p_num, snip = find_source_snippet(text, selected_diag[:25])
        findings["page_number"] = p_num
        findings["source_snippet"] = snip
    elif findings["histologic_type"]:
        findings["stated_diagnosis"] = findings["histologic_type"]

    # Tumor Grade / Differentiation
    grade_match = re.search(r"(?:Nottingham\s+(?:Histologic\s+)?Grade|Histologic(?:al)?\s+Grade|Gleason\s+Score|Differentiation|Grade)[\s:]+([^\n;\.]+)", text, re.IGNORECASE)
    if grade_match:
        findings["tumor_grade"] = grade_match.group(1).strip()

    # Margins
    margin_match = re.search(r"(?:Surgical\s+Margins?|Resection\s+Margins?|Margins?)[\s:]+([^\n;\.]+)", text, re.IGNORECASE)
    if margin_match:
        findings["surgical_margins"] = margin_match.group(1).strip()

    # Lymph Nodes
    node_match = re.search(r"(?:Lymph\s+Nodes?|Sentinel\s+Nodes?|Regional\s+Nodes?)[\s:]+([^\n;\.]+)", text, re.IGNORECASE)
    if node_match:
        findings["lymph_nodes"] = node_match.group(1).strip()

    # Lymphovascular Invasion (LVI)
    lvi_match = re.search(r"(?:Lymphovascular\s+Invasion|LVI|Vascular\s+Invasion)[\s:]+([^\n;\.]+)", text, re.IGNORECASE)
    if lvi_match:
        findings["lymphovascular_invasion"] = lvi_match.group(1).strip()

    # Perineural Invasion (PNI)
    pni_match = re.search(r"(?:Perineural\s+Invasion|PNI)[\s:]+([^\n;\.]+)", text, re.IGNORECASE)
    if pni_match:
        findings["perineural_invasion"] = pni_match.group(1).strip()

    # Pathologic Stage (pTNM)
    stage_match = re.search(r"(?:Pathologic\s+Stage|AJCC\s+Stage|pTNM)[\s:]+([^\n;\.]+)", text, re.IGNORECASE)
    if stage_match:
        findings["pathologic_stage"] = stage_match.group(1).strip()

    return findings


# ==============================================================================
# 3. Immunohistochemistry (IHC) Extractor
# ==============================================================================
IHC_MARKER_NAMES = [
    ("Estrogen Receptor (ER)", r"\b(?:Estrogen\s+Receptor|ER)\b[\s:]+([^\n;]+)"),
    ("Progesterone Receptor (PR)", r"\b(?:Progesterone\s+Receptor|PR)\b[\s:]+([^\n;]+)"),
    ("HER2 / neu", r"\b(?:HER2(?:\s*\/neu)?|c-erbB-2)\b[\s:]+([^\n;]+)"),
    ("Ki-67 Proliferation Index", r"\b(?:Ki[\s-]?67(?:\s+proliferation\s+index)?|MIB-1)\b[\s:]+([^\n;]+)"),
    ("PD-L1 Expression", r"\bPD[\s-]?L1(?:\s+CPS|\s+TPS)?[\s:]+([^\n;]+)"),
    ("Cytokeratin 7 (CK7)", r"\b(?:CK7|Cytokeratin\s+7)\b[\s:]+([^\n;]+)"),
    ("Cytokeratin 20 (CK20)", r"\b(?:CK20|Cytokeratin\s+20)\b[\s:]+([^\n;]+)"),
    ("TTF-1", r"\bTTF[\s-]1\b[\s:]+([^\n;]+)"),
    ("CDX2", r"\bCDX2\b[\s:]+([^\n;]+)"),
    ("p53", r"\bp53\b[\s:]+([^\n;]+)"),
    ("p16", r"\bp16\b[\s:]+([^\n;]+)"),
]


def extract_immunohistochemistry(text: str) -> List[Dict[str, Any]]:
    """Extracts IHC antibody results, staining percentages, intensities, and scores."""
    ihc_results = []

    for name, pattern in IHC_MARKER_NAMES:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_result = match.group(1).strip()
            cleaned_res = re.split(r"[\.,]\s*(?:Controls|Reference|Guidelines|Note|Method)", raw_result)[0].strip()

            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", cleaned_res)
            pct_val = pct_match.group(0) if pct_match else None

            if re.search(r"\bpositive\b", cleaned_res, re.IGNORECASE):
                status = "positive"
            elif re.search(r"\bnegative\b", cleaned_res, re.IGNORECASE):
                status = "negative"
            elif re.search(r"\bequivocal\b", cleaned_res, re.IGNORECASE):
                status = "equivocal"
            else:
                status = "reported"

            p_num, snippet = find_source_snippet(text, raw_result[:25])

            ihc_results.append({
                "marker": name,
                "result": cleaned_res,
                "status": status,
                "percentage": pct_val,
                "snippet": snippet,
                "page_number": p_num
            })

    return ihc_results


# ==============================================================================
# 4. Molecular Pathology & Genetic Tests Extractor
# ==============================================================================
GENE_MUTATION_PATTERNS = [
    ("EGFR", r"\bEGFR\b[^\n\.;]*(?:mutation|exon\s+19|exon\s+20|exon\s+21|l858r|t790m|deletion|wild[\s-]type)[^\n\.;]*"),
    ("KRAS", r"\bKRAS\b[^\n\.;]*(?:mutation|codon\s+12|codon\s+13|g12d|g12v|wild[\s-]type)[^\n\.;]*"),
    ("BRAF", r"\bBRAF\b[^\n\.;]*(?:mutation|v600e|v600k|wild[\s-]type)[^\n\.;]*"),
    ("BRCA1", r"\bBRCA1\b[^\n\.;]*(?:mutation|variant|pathogenic|benign|vus|wild[\s-]type)[^\n\.;]*"),
    ("BRCA2", r"\bBRCA2\b[^\n\.;]*(?:mutation|variant|pathogenic|benign|vus|wild[\s-]type)[^\n\.;]*"),
    ("ALK", r"\bALK\b[^\n\.;]*(?:rearrangement|fusion|translocation|negative|positive)[^\n\.;]*"),
    ("ROS1", r"\bROS1\b[^\n\.;]*(?:rearrangement|fusion|translocation|negative|positive)[^\n\.;]*"),
    ("MSI", r"\b(?:MSI|Microsatellite\s+Instability)\b[^\n\.;]*(?:high|msi-h|stable|mss|low|negative)[^\n\.;]*"),
]


def extract_molecular_genetics(text: str) -> List[Dict[str, Any]]:
    """Extracts molecular gene mutations, variants, and genomic findings."""
    results = []

    assay_match = re.search(r"(?:Assay|Test\s+Performed|Methodology|Panel\s+Name)[\s:]+([^\n\.;]+)", text, re.IGNORECASE)
    assay_name = assay_match.group(1).strip() if assay_match else "Molecular Diagnostic Panel"

    for gene, pattern in GENE_MUTATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            alteration_text = match.group(0).strip()
            if re.search(r"\b(?:wild[\s-]type|negative|no\s+mutation|not\s+detected)\b", alteration_text, re.IGNORECASE):
                sig = "Wild-type / Negative"
            elif re.search(r"\b(?:pathogenic|detected|positive|sensitizing)\b", alteration_text, re.IGNORECASE):
                sig = "Pathogenic / Alteration Detected"
            elif re.search(r"\bvus|variant\s+of\s+uncertain\b", alteration_text, re.IGNORECASE):
                sig = "Variant of Uncertain Significance (VUS)"
            else:
                sig = "Reported Finding"

            vaf_match = re.search(r"(\d+(?:\.\d+)?\s*%\s*(?:vaf|allele\s+fraction)?)", alteration_text, re.IGNORECASE)
            vaf_val = vaf_match.group(1) if vaf_match else None

            p_num, snippet = find_source_snippet(text, alteration_text[:30])

            results.append({
                "gene": gene,
                "test_name": assay_name,
                "alteration": alteration_text,
                "clinical_significance": sig,
                "vaf": vaf_val,
                "page_number": p_num,
                "snippet": snippet
            })

    return results


# ==============================================================================
# 5. Radiology and Imaging Extractor
# ==============================================================================
def extract_radiology(text: str) -> Dict[str, Any]:
    """Extracts radiology examination details, anatomical findings, and impression."""
    findings: Dict[str, Any] = {
        "modality": None,
        "study_name": None,
        "indication": None,
        "technique": None,
        "observations": [],
        "impression": None,
        "classification": None,
        "page_number": 1
    }

    study_match = re.search(r"(?:Examination|Study|Procedure|Scan)[\s:]+([^\n\.;]+)", text, re.IGNORECASE)
    if study_match:
        findings["study_name"] = study_match.group(1).strip()

    if re.search(r"\bpet[\s-]ct\b", text, re.IGNORECASE):
        findings["modality"] = "PET-CT"
    elif re.search(r"\bct\s+(?:scan|chest|abdomen|pelvis|head)\b", text, re.IGNORECASE):
        findings["modality"] = "Computed Tomography (CT)"
    elif re.search(r"\bmri\b|\bmagnetic\s+resonance\b", text, re.IGNORECASE):
        findings["modality"] = "Magnetic Resonance Imaging (MRI)"
    elif re.search(r"\bultrasound\b|\bsonograph", text, re.IGNORECASE):
        findings["modality"] = "Ultrasound"
    elif re.search(r"\bmammogra", text, re.IGNORECASE):
        findings["modality"] = "Mammography"

    ind_match = re.search(r"(?:Clinical\s+Indication|Indication|Reason\s+for\s+Exam|History)[\s:]+([^\n;]+)", text, re.IGNORECASE)
    if ind_match:
        findings["indication"] = ind_match.group(1).strip()

    tech_match = re.search(r"Technique[\s:]+([^\n]+(?:\n[^\n:]+)*?)(?=\n\s*(?:Findings|Comparison|Impression|$))", text, re.IGNORECASE)
    if tech_match:
        findings["technique"] = " ".join([l.strip() for l in tech_match.group(1).splitlines() if l.strip()])

    imp_match = re.search(r"(?:IMPRESSION|CONCLUSION|SUMMARY)[\s:]+([^\n]+(?:\n[^\n:]+)*?)(?=\n\s*(?:Radiologist|Attending|Dictated|Signed|$))", text, re.IGNORECASE)
    if imp_match:
        imp_clean = " ".join([l.strip() for l in imp_match.group(1).splitlines() if l.strip()])
        findings["impression"] = imp_clean
        p_num, _ = find_source_snippet(text, imp_clean[:30])
        findings["page_number"] = p_num

    birads_match = re.search(r"BI[\s-]RADS\s+(?:Category\s+)?(\d[a-cA-C]?)[^\n\.;]*", text, re.IGNORECASE)
    if birads_match:
        findings["classification"] = f"BI-RADS {birads_match.group(0).strip()}"

    recist_match = re.search(r"RECIST\s*(?:1\.1)?[\s:]+([^\n\.;]+)", text, re.IGNORECASE)
    if recist_match:
        findings["classification"] = f"RECIST: {recist_match.group(1).strip()}"

    organ_patterns = [
        ("Lungs & Pleura", r"(?:Lungs?|Pleura)[\s:]+([^\n;]+)"),
        ("Liver", r"Liver[\s:]+([^\n;]+)"),
        ("Lymph Nodes", r"(?:Lymph\s+Nodes?|Lymphadenopathy)[\s:]+([^\n;]+)"),
        ("Bones & Skeletal", r"(?:Bones?|Osseous\s+Structures?)[\s:]+([^\n;]+)"),
        ("Abdomen & Pelvis", r"(?:Abdomen|Pelvis|Spleen|Kidneys?)[\s:]+([^\n;]+)"),
    ]
    for organ, pat in organ_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            findings["observations"].append({
                "region": organ,
                "observation": m.group(1).strip()
            })

    return findings


# ==============================================================================
# 6. Complete Blood Count (CBC) & Routine Blood Tests Extractor
# ==============================================================================
CBC_ANALYTE_RULES = [
    {
        "name": "White Blood Cell Count (WBC)",
        "key": "wbc",
        "regex": r"(?:White\s+Blood\s+Cells?|WBC)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\^\d\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "x10^3/uL",
        "norm_low": 4.0,
        "norm_high": 11.0,
        "standard_ref": "4.0 - 11.0 x10^3/uL"
    },
    {
        "name": "Red Blood Cell Count (RBC)",
        "key": "rbc",
        "regex": r"(?:Red\s+Blood\s+Cells?|RBC)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\^\d\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "x10^6/uL",
        "norm_low": 4.0,
        "norm_high": 5.8,
        "standard_ref": "4.0 - 5.8 x10^6/uL"
    },
    {
        "name": "Hemoglobin",
        "key": "hemoglobin",
        "regex": r"(?:Hemoglobin|Hgb)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "g/dL",
        "norm_low": 12.0,
        "norm_high": 17.5,
        "standard_ref": "12.0 - 17.5 g/dL"
    },
    {
        "name": "Hematocrit",
        "key": "hematocrit",
        "regex": r"(?:Hematocrit|HCT|PCV)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*(%)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "%",
        "norm_low": 36.0,
        "norm_high": 50.0,
        "standard_ref": "36.0 - 50.0 %"
    },
    {
        "name": "Platelet Count",
        "key": "platelets",
        "regex": r"(?:Platelets?(?:\s+Count)?|PLT)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\^\d\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "x10^3/uL",
        "norm_low": 150.0,
        "norm_high": 450.0,
        "standard_ref": "150 - 450 x10^3/uL"
    },
    {
        "name": "Mean Corpuscular Volume (MCV)",
        "key": "mcv",
        "regex": r"\bMCV[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*(fL)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "fL",
        "norm_low": 80.0,
        "norm_high": 100.0,
        "standard_ref": "80.0 - 100.0 fL"
    },
    {
        "name": "Neutrophils",
        "key": "neutrophils",
        "regex": r"(?:Neutrophils?|Polys)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*(%)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "%",
        "norm_low": 40.0,
        "norm_high": 75.0,
        "standard_ref": "40.0 - 75.0 %"
    },
    {
        "name": "Lymphocytes",
        "key": "lymphocytes",
        "regex": r"Lymphocytes?[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*(%)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "%",
        "norm_low": 20.0,
        "norm_high": 45.0,
        "standard_ref": "20.0 - 45.0 %"
    },
]


def extract_cbc_analytes(text: str) -> List[Dict[str, Any]]:
    """Extracts Complete Blood Count (CBC) parameters with units and reference ranges."""
    results = []

    for rule in CBC_ANALYTE_RULES:
        match = re.search(rule["regex"], text, re.IGNORECASE)
        if match:
            raw_val = match.group(1).strip()
            raw_unit = match.group(2).strip() if match.group(2) else None
            raw_ref = match.group(3).strip() if match.group(3) else None

            val_clean = raw_val.replace("<", "").replace(">", "").strip()
            try:
                num_val = float(val_clean)
            except ValueError:
                num_val = raw_val

            status = "normal"
            if isinstance(num_val, (int, float)):
                if num_val < rule["norm_low"]:
                    status = "low"
                elif num_val > rule["norm_high"]:
                    status = "elevated"

            p_num, snippet = find_source_snippet(text, raw_val)

            results.append({
                "name": rule["name"],
                "key": rule["key"],
                "value": num_val,
                "unit": raw_unit,
                "reference_range": raw_ref,
                "status": status,
                "snippet": snippet,
                "page_number": p_num
            })

    return results


# ==============================================================================
# 7. Biochemistry & Metabolic Panels Extractor
# ==============================================================================
BIOCHEM_ANALYTE_RULES = [
    {
        "name": "Fasting Blood Glucose",
        "key": "glucose",
        "regex": r"(?:Fasting\s+(?:Blood\s+)?Glucose|Fasting\s+Blood\s+Sugar)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mg/dL",
        "norm_low": 70.0,
        "norm_high": 99.0,
        "standard_ref": "70 - 99 mg/dL"
    },
    {
        "name": "Blood Urea Nitrogen (BUN)",
        "key": "bun",
        "regex": r"(?:Blood\s+Urea\s+Nitrogen|BUN)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mg/dL",
        "norm_low": 7.0,
        "norm_high": 20.0,
        "standard_ref": "7 - 20 mg/dL"
    },
    {
        "name": "Serum Creatinine",
        "key": "creatinine",
        "regex": r"(?:Serum\s+Creatinine|Creatinine)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mg/dL",
        "norm_low": 0.6,
        "norm_high": 1.2,
        "standard_ref": "0.6 - 1.2 mg/dL"
    },
    {
        "name": "eGFR",
        "key": "egfr",
        "regex": r"(?:eGFR|Estimated\s+GFR)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/\d\.\^]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mL/min/1.73m2",
        "norm_low": 60.0,
        "norm_high": 120.0,
        "standard_ref": "> 60 mL/min/1.73m2"
    },
    {
        "name": "Total Cholesterol",
        "key": "total_cholesterol",
        "regex": r"(?:Total\s+Cholesterol|Cholesterol)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mg/dL",
        "norm_low": 120.0,
        "norm_high": 200.0,
        "standard_ref": "< 200 mg/dL"
    },
    {
        "name": "Serum Potassium",
        "key": "potassium",
        "regex": r"(?:Serum\s+Potassium|Potassium)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mEq/L",
        "norm_low": 3.5,
        "norm_high": 5.1,
        "standard_ref": "3.5 - 5.1 mEq/L"
    },
    {
        "name": "Serum Sodium",
        "key": "sodium",
        "regex": r"(?:Serum\s+Sodium|Sodium)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mEq/L",
        "norm_low": 135.0,
        "norm_high": 145.0,
        "standard_ref": "135 - 145 mEq/L"
    },
    {
        "name": "ALT (SGPT)",
        "key": "alt",
        "regex": r"(?:ALT|SGPT|Alanine\s+Aminotransferase)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "U/L",
        "norm_low": 7.0,
        "norm_high": 56.0,
        "standard_ref": "7 - 56 U/L"
    },
    {
        "name": "AST (SGOT)",
        "key": "ast",
        "regex": r"(?:AST|SGOT|Aspartate\s+Aminotransferase)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "U/L",
        "norm_low": 10.0,
        "norm_high": 40.0,
        "standard_ref": "10 - 40 U/L"
    },
    {
        "name": "Total Bilirubin",
        "key": "total_bilirubin",
        "regex": r"(?:Total\s+Bilirubin|Bilirubin\s+Total)[\s:]+([<>]?\s*\d+(?:\.\d+)?)\s*([a-zA-Z\/]+)?(?:\s*[\(\[]?(?:ref|reference)?[\s:]*([<>]?\s*[\d\.\s\-–to]+)[\)\]]?)?",
        "default_unit": "mg/dL",
        "norm_low": 0.1,
        "norm_high": 1.2,
        "standard_ref": "0.1 - 1.2 mg/dL"
    },
]


def extract_biochemistry_analytes(text: str) -> List[Dict[str, Any]]:
    """Extracts clinical biochemistry / metabolic panel parameters."""
    results = []

    for rule in BIOCHEM_ANALYTE_RULES:
        match = re.search(rule["regex"], text, re.IGNORECASE)
        if match:
            raw_val = match.group(1).strip()
            raw_unit = match.group(2).strip() if match.group(2) else None
            raw_ref = match.group(3).strip() if match.group(3) else None

            val_clean = raw_val.replace("<", "").replace(">", "").strip()
            try:
                num_val = float(val_clean)
            except ValueError:
                num_val = raw_val

            status = "normal"
            if isinstance(num_val, (int, float)):
                if num_val < rule["norm_low"]:
                    status = "low"
                elif num_val > rule["norm_high"]:
                    status = "elevated"

            p_num, snippet = find_source_snippet(text, raw_val)

            results.append({
                "name": rule["name"],
                "key": rule["key"],
                "value": num_val,
                "unit": raw_unit,
                "reference_range": raw_ref,
                "status": status,
                "snippet": snippet,
                "page_number": p_num
            })

    return results


# ==============================================================================
# Master Unified Extractor
# ==============================================================================
def extract_structured_findings(
    text: str,
    category_id: str,
    title: str = ""
) -> Dict[str, Any]:
    """
    Main extraction coordinator: Extracts category-specific parameters and findings.
    Also extracts secondary findings (e.g. tumor markers in a blood test) if present.
    """
    findings: Dict[str, Any] = {
        "category_id": category_id,
        "specimen": None,
        "diagnosis": None,
        "tumor_markers": [],
        "ihc_markers": [],
        "molecular_tests": [],
        "radiology": None,
        "laboratory_parameters": [],
        "vitals_for_twin": [],
        "missing_fields": [],
        "page_references": []
    }

    if not text or not text.strip():
        return findings

    # Category-specific extraction
    if category_id == ReportCategory.TUMOUR_MARKERS:
        findings["tumor_markers"] = extract_tumor_markers(text)

    elif category_id == ReportCategory.HISTOPATHOLOGY_BIOPSY:
        hp = extract_histopathology(text)
        findings["diagnosis"] = hp
        findings["specimen"] = {
            "site": hp["specimen_site"],
            "procedure": hp["procedure"],
        }
        ihc = extract_immunohistochemistry(text)
        if ihc:
            findings["ihc_markers"] = ihc

    elif category_id == ReportCategory.IMMUNOHISTOCHEMISTRY:
        findings["ihc_markers"] = extract_immunohistochemistry(text)
        hp = extract_histopathology(text)
        if hp.get("stated_diagnosis") or hp.get("specimen_site"):
            findings["diagnosis"] = hp

    elif category_id == ReportCategory.MOLECULAR_GENETICS:
        findings["molecular_tests"] = extract_molecular_genetics(text)

    elif category_id == ReportCategory.RADIOLOGY_IMAGING:
        findings["radiology"] = extract_radiology(text)

    elif category_id == ReportCategory.CBC_ROUTINE_BLOOD:
        findings["laboratory_parameters"] = extract_cbc_analytes(text)

    elif category_id == ReportCategory.BIOCHEMISTRY_METABOLIC:
        findings["laboratory_parameters"] = extract_biochemistry_analytes(text)

    elif category_id in [ReportCategory.OTHER_MEDICAL, ReportCategory.UNCERTAIN]:
        purpose = re.search(r"(?:Report\s+purpose|Purpose|Clinical\s+Indication)[\s:]*\n?\s*([^\n]+)", text, re.IGNORECASE)
        context = re.search(r"(?:1\.\s*Clinical\s+context|Clinical\s+context|Context)[\s:]*\n?\s*([^\n]+(?:\n(?!\d+\.)[^\n]+)*)", text, re.IGNORECASE)
        assess = re.search(r"(?:2\.\s*Illustrative\s+assessment\s+wording|Assessment|Clinical\s+Impression)[\s:]*\n?\s*([^\n]+(?:\n(?!\d+\.)[^\n]+)*)", text, re.IGNORECASE)
        next_steps = re.search(r"(?:3\.\s*Suggested\s+next\s+steps|Next\s+steps|Recommendations?)[\s:]*\n?\s*([^\n]+(?:\n(?!\d+\.)[^\n]+)*)", text, re.IGNORECASE)
        limits = re.search(r"(?:4\.\s*Important\s+limitation|Limitations?|Notice)[\s:]*\n?\s*([^\n]+(?:\n(?!\d+\.)[^\n]+)*)", text, re.IGNORECASE)

        if purpose or context or next_steps or limits:
            findings["consultation_notes"] = {
                "purpose": purpose.group(1).strip() if purpose else None,
                "context": " ".join(context.group(1).split()) if context else None,
                "assessment": " ".join(assess.group(1).split()) if assess else None,
                "next_steps": " ".join(next_steps.group(1).split()) if next_steps else None,
                "limitations": " ".join(limits.group(1).split()) if limits else None,
            }

    # Cross-check for secondary findings:
    if category_id not in [ReportCategory.TUMOUR_MARKERS]:
        secondary_tm = extract_tumor_markers(text)
        if secondary_tm:
            findings["tumor_markers"] = secondary_tm

    if category_id not in [ReportCategory.CBC_ROUTINE_BLOOD, ReportCategory.BIOCHEMISTRY_METABOLIC]:
        cbc_items = extract_cbc_analytes(text)
        if cbc_items:
            findings["laboratory_parameters"].extend(cbc_items)
        biochem_items = extract_biochemistry_analytes(text)
        if biochem_items:
            findings["laboratory_parameters"].extend(biochem_items)

    # Extract physiological vitals (HR, BP, SpO2) for Digital Twin sync
    hr_match = re.search(r'(?:Heart Rate|Pulse Rate|Pulse|HR)[\s:]+(\d{2,3}(?:\.\d+)?)\s*(?:bpm)?', text, re.IGNORECASE)
    if hr_match:
        val = float(hr_match.group(1))
        if 30.0 <= val <= 250.0:
            findings["vitals_for_twin"].append({
                "name": "Heart Rate",
                "key": "heart_rate",
                "value": val,
                "unit": "bpm",
                "reference_range": "60 - 100 bpm",
                "status": "normal" if 60 <= val <= 100 else ("elevated" if val > 100 else "low"),
                "confidence": "high",
                "requires_confirmation": True
            })

    # Track missing fields for transparency
    if category_id == ReportCategory.TUMOUR_MARKERS:
        for tm in findings["tumor_markers"]:
            if not tm.get("unit"):
                findings["missing_fields"].append(f"Unit missing for {tm['name']}")
            if not tm.get("reference_range"):
                findings["missing_fields"].append(f"Reference range missing for {tm['name']}")

    if category_id == ReportCategory.HISTOPATHOLOGY_BIOPSY:
        hp = findings.get("diagnosis") or {}
        has_diag = bool(hp.get("stated_diagnosis") or hp.get("histologic_type") or hp.get("is_benign_or_negative"))
        if not has_diag:
            findings["missing_fields"].append("Histopathologic diagnosis not explicitly stated in text")

    return findings

