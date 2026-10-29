"""
Medical Report Classification Service for Sovereign Health Twin.
Accurately categorizes clinical documents using textual evidence from headers,
methodology, specimen descriptions, and diagnostic terminology without forcing
all documents into cardiovascular/metabolic buckets.
"""

import re
from typing import Dict, Any, List, Tuple


class ReportCategory:
    CBC_ROUTINE_BLOOD = "cbc_routine_blood"
    BIOCHEMISTRY_METABOLIC = "biochemistry_metabolic"
    TUMOUR_MARKERS = "tumour_markers"
    HISTOPATHOLOGY_BIOPSY = "histopathology_biopsy"
    IMMUNOHISTOCHEMISTRY = "immunohistochemistry"
    MOLECULAR_GENETICS = "molecular_genetics"
    RADIOLOGY_IMAGING = "radiology_imaging"
    OTHER_MEDICAL = "other_medical"
    UNCERTAIN = "uncertain"


CATEGORY_DISPLAY_NAMES = {
    ReportCategory.CBC_ROUTINE_BLOOD: "Complete blood count (CBC) and routine blood tests",
    ReportCategory.BIOCHEMISTRY_METABOLIC: "Biochemistry and metabolic panels",
    ReportCategory.TUMOUR_MARKERS: "Tumour-marker tests",
    ReportCategory.HISTOPATHOLOGY_BIOPSY: "Histopathology and biopsy reports",
    ReportCategory.IMMUNOHISTOCHEMISTRY: "Immunohistochemistry (IHC) reports",
    ReportCategory.MOLECULAR_GENETICS: "Molecular pathology and genetic test reports",
    ReportCategory.RADIOLOGY_IMAGING: "Radiology and imaging reports",
    ReportCategory.OTHER_MEDICAL: "Other medical reports and unknown document types",
    ReportCategory.UNCERTAIN: "Report type uncertain",
}

# Strong definitive header indicators (weight = 6)
PRIMARY_HEADER_RULES: List[Tuple[str, str, int]] = [
    # Tumour Markers
    (r"(?:tumor|tumour)\s+marker", ReportCategory.TUMOUR_MARKERS, 7),
    (r"serum\s+tumor\s+markers?", ReportCategory.TUMOUR_MARKERS, 8),
    (r"oncology\s+biomarkers?", ReportCategory.TUMOUR_MARKERS, 7),
    (r"prostate\s+specific\s+antigen|psa\s+panel", ReportCategory.TUMOUR_MARKERS, 7),

    # Histopathology & Biopsy
    (r"surgical\s+pathology\s+report", ReportCategory.HISTOPATHOLOGY_BIOPSY, 9),
    (r"histopathol(?:ogy|ogical)\s+(?:report|examination|diagnosis)", ReportCategory.HISTOPATHOLOGY_BIOPSY, 9),
    (r"(?:core|punch|needle|excisional|incisional)\s+biopsy\s+report", ReportCategory.HISTOPATHOLOGY_BIOPSY, 9),
    (r"gross\s+and\s+microscopic\s+examination", ReportCategory.HISTOPATHOLOGY_BIOPSY, 8),
    (r"pathology\s+consultation\s+report", ReportCategory.HISTOPATHOLOGY_BIOPSY, 8),

    # Immunohistochemistry (IHC)
    (r"immunohistochem(?:istry|ical)\s+(?:report|profile|staining|panel|study)", ReportCategory.IMMUNOHISTOCHEMISTRY, 9),
    (r"ihc\s+(?:report|profile|panel|results?)", ReportCategory.IMMUNOHISTOCHEMISTRY, 9),
    (r"breast\s+biomarker\s+(?:panel|profile)\s+\(ihc\)", ReportCategory.IMMUNOHISTOCHEMISTRY, 9),

    # Molecular Genetics
    (r"molecular\s+pathology\s+report", ReportCategory.MOLECULAR_GENETICS, 9),
    (r"molecular\s+diagnostics?\s+laboratory", ReportCategory.MOLECULAR_GENETICS, 8),
    (r"next\s+generation\s+sequencing\s+(?:report|panel|analysis)", ReportCategory.MOLECULAR_GENETICS, 9),
    (r"ngs\s+(?:oncology|somatic|germline)\s+panel", ReportCategory.MOLECULAR_GENETICS, 9),
    (r"(?:gene\s+)?mutation\s+analysis\s+report", ReportCategory.MOLECULAR_GENETICS, 9),
    (r"liquid\s+biopsy\s+genomic\s+profile", ReportCategory.MOLECULAR_GENETICS, 9),

    # Radiology & Imaging
    (r"department\s+of\s+radiology|diagnostic\s+imaging\s+report", ReportCategory.RADIOLOGY_IMAGING, 8),
    (r"computed\s+tomography\s+(?:ct\s+)?report", ReportCategory.RADIOLOGY_IMAGING, 9),
    (r"(?:ct|mri|pet-ct|ultrasound|mammograph[a-z]*)\s+(?:report|examination|scan)", ReportCategory.RADIOLOGY_IMAGING, 8),
    (r"magnetic\s+resonance\s+imaging\s+report", ReportCategory.RADIOLOGY_IMAGING, 9),
    (r"positron\s+emission\s+tomography", ReportCategory.RADIOLOGY_IMAGING, 9),

    # CBC / Routine Blood
    (r"complete\s+blood\s+count\s*(?:\(cbc\))?", ReportCategory.CBC_ROUTINE_BLOOD, 9),
    (r"hemogram\s+report|complete\s+blood\s+picture", ReportCategory.CBC_ROUTINE_BLOOD, 9),
    (r"hematology\s+laboratory\s+report", ReportCategory.CBC_ROUTINE_BLOOD, 7),

    # Biochemistry & Metabolic
    (r"comprehensive\s+metabolic\s+panel\s*(?:\(cmp\))?", ReportCategory.BIOCHEMISTRY_METABOLIC, 9),
    (r"basic\s+metabolic\s+panel\s*(?:\(bmp\))?", ReportCategory.BIOCHEMISTRY_METABOLIC, 9),
    (r"clinical\s+biochemistry\s+report", ReportCategory.BIOCHEMISTRY_METABOLIC, 7),
    (r"liver\s+function\s+tests?\s*(?:\(lft\))?", ReportCategory.BIOCHEMISTRY_METABOLIC, 8),
    (r"renal\s+function\s+tests?\s*(?:\(rft\))?", ReportCategory.BIOCHEMISTRY_METABOLIC, 8),
    (r"lipid\s+panel|lipid\s+profile", ReportCategory.BIOCHEMISTRY_METABOLIC, 8),
]

# Characteristic domain keywords and weights
DOMAIN_KEYWORD_RULES: Dict[str, List[Tuple[str, int, str]]] = {
    ReportCategory.TUMOUR_MARKERS: [
        (r"\bpsa\b|\bprostate[\s-]specific\s+antigen\b", 3, "PSA marker"),
        (r"\bfree\s+psa\b", 3, "Free PSA"),
        (r"\bcea\b|\bcarcinoembryonic\s+antigen\b", 3, "CEA marker"),
        (r"\bca[\s-]?125\b", 3, "CA-125 marker"),
        (r"\bca[\s-]?19[\s-]?9\b", 3, "CA 19-9 marker"),
        (r"\bca[\s-]?15[\s-]?3\b", 3, "CA 15-3 marker"),
        (r"\bafp\b|\balpha[\s-]fetoprotein\b", 3, "AFP marker"),
        (r"\bbeta[\s-]hcg\b|\bb-hcg\b", 2, "Beta-hCG marker"),
        (r"\bchromogranin\s+a\b", 3, "Chromogranin A"),
        (r"\bthyroglobulin\b", 2, "Thyroglobulin"),
        (r"\bcalcitonin\b", 2, "Calcitonin"),
    ],
    ReportCategory.HISTOPATHOLOGY_BIOPSY: [
        (r"\bnottingham\s+(?:histologic\s+)?grade\b|\bnottingham\s+score\b", 4, "Nottingham histologic grade"),
        (r"\bgleason\s+(?:score|pattern|grade\s+group)\b", 4, "Gleason score"),
        (r"\binvasive\s+ductal\s+carcinoma\b|\bidc\b", 4, "Invasive ductal carcinoma"),
        (r"\binvasive\s+lobular\s+carcinoma\b", 4, "Invasive lobular carcinoma"),
        (r"\badenocarcinoma\b", 3, "Adenocarcinoma"),
        (r"\bsquamous\s+cell\s+carcinoma\b", 3, "Squamous cell carcinoma"),
        (r"\bhistologic\s+grade\s*:\s*(?:grade\s*)?[123iIvVxX]+", 3, "Histologic grade"),
        (r"\b(?:well|moderately|poorly)\s+differentiated\b", 3, "Tumor differentiation"),
        (r"\bsurgical\s+margins?\s*:\s*(?:negative|positive|involved|clear|free)", 3, "Surgical margins status"),
        (r"\blymph\s+nodes?\s*:\s*\d+\s*(?:of|\/)\s*\d+", 3, "Lymph node involvement ratio"),
        (r"\blymphovascular\s+invasion\s*:\s*(?:present|identified|not\s+identified|absent|negative)", 3, "Lymphovascular invasion"),
        (r"\bperineural\s+invasion\s*:\s*(?:present|not\s+identified|absent|negative)", 3, "Perineural invasion"),
        (r"\bpathologic\s+stage\s*:\s*p[tT][0-9a-zA-Z]+", 4, "Pathologic pTNM staging"),
        (r"\bmicroscopic\s+description\b", 2, "Microscopic description"),
        (r"\bgross\s+description\b", 2, "Gross description"),
        (r"\bcore\s+biopsy\b|\bexcision\s+specimen\b", 2, "Biopsy specimen reference"),
    ],
    ReportCategory.IMMUNOHISTOCHEMISTRY: [
        (r"\bestrogen\s+receptor\b|\ber\s*:\s*(?:positive|negative|\d+%)", 4, "Estrogen Receptor (ER)"),
        (r"\bprogesterone\s+receptor\b|\bpr\s*:\s*(?:positive|negative|\d+%)", 4, "Progesterone Receptor (PR)"),
        (r"\bher2\s*(?:\/neu)?\s*:\s*(?:positive|negative|equivocal|score\s*[0-3]\+?)", 4, "HER2 / neu status"),
        (r"\bki[\s-]?67\b(?:\s+proliferation\s+index|\s+labeling\s+index)?", 4, "Ki-67 proliferation index"),
        (r"\ballred\s+score\b", 3, "Allred score"),
        (r"\basco[\s\/]cap\s+guidelines?\b", 3, "ASCO/CAP guideline criteria"),
        (r"\bpd[\s-]?l1\b(?:\s+cps|\s+tps|\s+expression)?", 4, "PD-L1 expression"),
        (r"\bck7\b|\bcytokeratin\s+7\b", 2, "Cytokeratin 7 (CK7)"),
        (r"\bck20\b|\bcytokeratin\s+20\b", 2, "Cytokeratin 20 (CK20)"),
        (r"\bttf[\s-]1\b", 2, "TTF-1 marker"),
        (r"\bcdx2\b", 2, "CDX2 marker"),
        (r"\bp53\s+(?:expression|immunostain)\b", 2, "p53 immunostain"),
        (r"\bp16\s+(?:expression|immunostain|positive|negative)\b", 2, "p16 immunostain"),
    ],
    ReportCategory.MOLECULAR_GENETICS: [
        (r"\begfr\b(?:\s+mutation|\s+exon\s+19|\s+l858r|\s+t790m)?", 4, "EGFR gene alteration"),
        (r"\bkras\b(?:\s+mutation|\s+codon\s+12|\s+g12d|\s+wild[\s-]type)?", 4, "KRAS alteration"),
        (r"\bbraf\b(?:\s+v600e|\s+mutation)?", 4, "BRAF mutation"),
        (r"\bbrca1\b|\bbrca2\b", 4, "BRCA1 / BRCA2 variant"),
        (r"\balk\s+(?:rearrangement|fusion|translocation)\b", 4, "ALK rearrangement"),
        (r"\bros1\s+(?:rearrangement|fusion)\b", 4, "ROS1 fusion"),
        (r"\bmicrosatellite\s+instability\b|\bmsi[\s-]h\b|\bmss\b", 4, "MSI status"),
        (r"\bmismatch\s+repair\b|\bdmmr\b|\bpmmr\b", 4, "MMR status"),
        (r"\bpathogenic\s+variant\b|\bvariant\s+of\s+uncertain\s+significance\b|\bvus\b", 3, "Variant classification"),
        (r"\ballele\s+frequency\b|\bvaf\b", 2, "Variant allele frequency (VAF)"),
        (r"\bexon\s+(?:18|19|20|21)\b", 2, "Specific exon mutation scan"),
        (r"\bwild[\s-]type\b", 2, "Wild-type genomic finding"),
    ],
    ReportCategory.RADIOLOGY_IMAGING: [
        (r"\bct\s+(?:chest|abdomen|pelvis|head|brain|spine|thorax)\b", 4, "CT study protocol"),
        (r"\bmri\s+(?:brain|spine|pelvis|breast|knee|abdomen)\b", 4, "MRI study protocol"),
        (r"\bpet[\s-]ct\s+(?:whole\s+body|skull\s+to\s+thigh)\b", 4, "PET-CT imaging protocol"),
        (r"\biv\s+contrast\b|\boral\s+contrast\b", 2, "Contrast administration"),
        (r"\bcontrast[\s-]enhanced\b", 2, "Contrast-enhanced technique"),
        (r"\btechnique\s*:.*?(?:slice|axial|helical|detector)", 3, "Radiological technique"),
        (r"\bfindings\s*:.*?(?:lungs?|liver|nodes?|bones?)", 3, "Organ-specific imaging findings"),
        (r"\bimpression\s*:\s*[^\n]+", 2, "Radiologist impression statement"),
        (r"\bbirads\b|\bbi[\s-]rads\s+category\b", 4, "BI-RADS score"),
        (r"\brecist\s+(?:1\.1|criteria)?", 4, "RECIST criteria assessment"),
        (r"\bhypodense\b|\bhyperdense\b|\battenuation\b|\benhancing\s+lesion\b", 3, "Imaging radiodensity terms"),
    ],
    ReportCategory.CBC_ROUTINE_BLOOD: [
        (r"\bwhite\s+blood\s+cells?\b|\bwbc\b", 3, "WBC count"),
        (r"\bred\s+blood\s+cells?\b|\brbc\b", 3, "RBC count"),
        (r"\bplatelets?(?:\s+count)?\b|\bplt\b", 3, "Platelet count"),
        (r"\bhematocrit\b|\bhct\b|\bpcv\b", 3, "Hematocrit"),
        (r"\bmcv\b|\bmch\b|\bmchc\b|\brdw\b", 3, "Red blood cell indices"),
        (r"\bneutrophils?\b|\blymphocytes?\b|\bmonocytes?\b|\beosinophils?\b", 2, "Differential white blood count"),
        (r"\bhemoglobin\b|\bhgb\b", 2, "Hemoglobin test"),
    ],
    ReportCategory.BIOCHEMISTRY_METABOLIC: [
        (r"\bblood\s+urea\s+nitrogen\b|\bbun\b", 3, "BUN level"),
        (r"\bserum\s+creatinine\b|\bcreatinine\b", 3, "Serum Creatinine"),
        (r"\begfr\b|\bglomerular\s+filtration\s+rate\b", 3, "eGFR rate"),
        (r"\bfasting\s+(?:blood\s+)?glucose\b|\bblood\s+sugar\b", 3, "Fasting glucose"),
        (r"\bhba1c\b|\bglycated\s+hemoglobin\b", 3, "HbA1c level"),
        (r"\bserum\s+sodium\b|\bpotassium\b|\bchloride\b|\bbicarbonate\b", 2, "Electrolyte panel"),
        (r"\btotal\s+bilirubin\b|\bdirect\s+bilirubin\b", 3, "Bilirubin panel"),
        (r"\balt\b|\bsgpt\b|\bast\b|\bsgot\b", 3, "Liver transaminases (ALT/AST)"),
        (r"\balkaline\s+phosphatase\b|\balp\b", 2, "Alkaline Phosphatase"),
        (r"\btotal\s+cholesterol\b|\btriglycerides\b|\bhdl\b|\bldl\b", 3, "Lipid profile markers"),
        (r"\btotal\s+protein\b|\bserum\s+albumin\b", 2, "Serum protein / albumin"),
    ],
}


def classify_medical_report(text: str, title: str = "") -> Dict[str, Any]:
    """
    Examines report text and title to classify the medical document into an evidence-backed category.
    Returns:
        {
            "category_id": str,
            "category_name": str,
            "confidence": "high" | "moderate" | "low",
            "evidence": List[str],
            "all_scores": Dict[str, int],
            "secondary_categories": List[Dict[str, Any]]
        }
    """
    clean_text = (text or "").lower()
    clean_title = (title or "").lower()
    combined_content = f"{clean_title}\n{clean_text}"

    scores: Dict[str, int] = {cat: 0 for cat in [
        ReportCategory.CBC_ROUTINE_BLOOD,
        ReportCategory.BIOCHEMISTRY_METABOLIC,
        ReportCategory.TUMOUR_MARKERS,
        ReportCategory.HISTOPATHOLOGY_BIOPSY,
        ReportCategory.IMMUNOHISTOCHEMISTRY,
        ReportCategory.MOLECULAR_GENETICS,
        ReportCategory.RADIOLOGY_IMAGING,
    ]}
    evidence_collected: Dict[str, List[str]] = {cat: [] for cat in scores}

    # 1. Evaluate Primary Header Rules (Strong signals)
    for pattern, cat, weight in PRIMARY_HEADER_RULES:
        match = re.search(pattern, combined_content, re.IGNORECASE)
        if match:
            scores[cat] += weight
            matched_phrase = match.group(0).strip()
            evidence_collected[cat].append(f"Header/Title match: '{matched_phrase}' (+{weight})")

    # 2. Evaluate Domain Keywords
    for cat, rules in DOMAIN_KEYWORD_RULES.items():
        for pattern, weight, label in rules:
            matches = list(re.finditer(pattern, clean_text, re.IGNORECASE))
            if matches:
                # Cap contribution to avoid single word repetition blowing up score
                count = min(len(matches), 3)
                earned = count * weight
                scores[cat] += earned
                snippet = matches[0].group(0)
                evidence_collected[cat].append(f"{label} ('{snippet}' x{len(matches)}) (+{earned})")

    # Sort categories by score descending
    sorted_cats = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_cat, top_score = sorted_cats[0]

    # Check for empty / unreadable / insufficient signal
    word_count = len(clean_text.split())
    if word_count < 10 and top_score < 4:
        return {
            "category_id": ReportCategory.UNCERTAIN,
            "category_name": CATEGORY_DISPLAY_NAMES[ReportCategory.UNCERTAIN],
            "confidence": "low",
            "evidence": ["Document contains insufficient text to classify confidently (< 10 words)."],
            "all_scores": scores,
            "secondary_categories": []
        }

    # If no category scored any points
    if top_score == 0:
        # Check if it has any general medical terms
        general_medical_patterns = [
            r"\bpatient\b", r"\bphysician\b", r"\bdr\.\b", r"\bhospital\b",
            r"\bclinic\b", r"\bdiagnosis\b", r"\bexamination\b", r"\bprescription\b",
            r"\bconsultation\b", r"\bhistory\s+of\s+present\s+illness\b", r"\btreatment\b"
        ]
        gen_matches = [p for p in general_medical_patterns if re.search(p, clean_text)]
        if len(gen_matches) >= 2:
            return {
                "category_id": ReportCategory.OTHER_MEDICAL,
                "category_name": CATEGORY_DISPLAY_NAMES[ReportCategory.OTHER_MEDICAL],
                "confidence": "low",
                "evidence": [f"General clinical document markers found ({', '.join(gen_matches)}), but no specific oncology or lab panel detected."],
                "all_scores": scores,
                "secondary_categories": []
            }
        else:
            return {
                "category_id": ReportCategory.UNCERTAIN,
                "category_name": CATEGORY_DISPLAY_NAMES[ReportCategory.UNCERTAIN],
                "confidence": "low",
                "evidence": ["No recognizable diagnostic, oncology, laboratory, or radiology markers found in document."],
                "all_scores": scores,
                "secondary_categories": []
            }

    # Determine confidence based on top score and margin over runner-up
    second_cat, second_score = sorted_cats[1] if len(sorted_cats) > 1 else ("", 0)

    # Specific override: If IHC and Histopathology are both high, check which is primary
    # If text specifically says "Immunohistochemical Profile" or "IHC Report", IHC takes precedence
    if top_cat == ReportCategory.HISTOPATHOLOGY_BIOPSY and scores[ReportCategory.IMMUNOHISTOCHEMISTRY] >= 7:
        if re.search(r"immunohistochem|ihc\s+report|ihc\s+profile", combined_content):
            top_cat = ReportCategory.IMMUNOHISTOCHEMISTRY
            top_score = scores[ReportCategory.IMMUNOHISTOCHEMISTRY]

    if top_score >= 8 or (top_score >= 6 and top_score >= second_score * 1.5):
        confidence = "high"
    elif top_score >= 4:
        confidence = "moderate"
    else:
        confidence = "low"

    # Secondary categories with meaningful scores (>= 4)
    secondary_categories = []
    for cat, sc in sorted_cats:
        if cat != top_cat and sc >= 4:
            secondary_categories.append({
                "category_id": cat,
                "category_name": CATEGORY_DISPLAY_NAMES[cat],
                "score": sc,
                "evidence": evidence_collected[cat][:3]
            })

    # If top score is very weak (1 or 2) and runner up is close
    if top_score < 3:
        return {
            "category_id": ReportCategory.UNCERTAIN,
            "category_name": CATEGORY_DISPLAY_NAMES[ReportCategory.UNCERTAIN],
            "confidence": "low",
            "evidence": [f"Signals too weak to classify confidently (top category '{CATEGORY_DISPLAY_NAMES[top_cat]}' scored only {top_score})."] + evidence_collected[top_cat],
            "all_scores": scores,
            "secondary_categories": secondary_categories
        }

    return {
        "category_id": top_cat,
        "category_name": CATEGORY_DISPLAY_NAMES[top_cat],
        "confidence": confidence,
        "evidence": evidence_collected[top_cat],
        "all_scores": scores,
        "secondary_categories": secondary_categories
    }
