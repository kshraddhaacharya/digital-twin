import io
import csv
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import dateutil.parser
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.measurement import Measurement
from app.models.patient import Patient
from app.schemas.measurement import VALID_UNITS, VALUE_BOUNDS


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses arbitrary ISO or standard datetime strings into UTC datetime."""
    try:
        dt = dateutil.parser.isoparse(dt_str)
    except Exception:
        dt = dateutil.parser.parse(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def validate_measurement_row(row: Dict[str, Any], row_idx: int) -> Tuple[Dict[str, Any], str]:
    """
    Validates a single row of measurement data against strict physiological rules.
    Returns (validated_data, "") on success or ({}, error_message) on failure.
    """
    # 1. Timestamp validation
    raw_ts = row.get("timestamp")
    if not raw_ts:
        return {}, f"Row {row_idx}: Missing 'timestamp' field"
    try:
        ts = parse_iso_datetime(str(raw_ts).strip())
    except Exception as e:
        return {}, f"Row {row_idx}: Invalid timestamp '{raw_ts}': {str(e)}"

    # 2. Measurement type validation
    raw_type = str(row.get("measurement_type", "")).strip().lower()
    if not raw_type:
        return {}, f"Row {row_idx}: Missing 'measurement_type'"
    if raw_type not in VALID_UNITS:
        allowed = ", ".join(VALID_UNITS.keys())
        return {}, f"Row {row_idx}: Unsupported measurement_type '{raw_type}'. Allowed types: {allowed}"

    # 3. Unit validation
    raw_unit = str(row.get("unit", "")).strip()
    if not raw_unit:
        return {}, f"Row {row_idx}: Missing 'unit'"
    valid_units = VALID_UNITS[raw_type]
    if raw_unit not in valid_units and raw_unit.lower() not in [u.lower() for u in valid_units]:
        return {}, f"Row {row_idx}: Invalid unit '{raw_unit}' for '{raw_type}'. Allowed: {valid_units}"

    # 4. Numeric value validation
    raw_val = row.get("value")
    if raw_val is None or str(raw_val).strip() == "":
        return {}, f"Row {row_idx}: Missing 'value'"
    try:
        val = float(raw_val)
    except (ValueError, TypeError):
        return {}, f"Row {row_idx}: Non-numeric value '{raw_val}'"

    min_v, max_v, msg = VALUE_BOUNDS[raw_type]
    if raw_type == "body_temperature" and "f" in raw_unit.lower():
        if not (86.0 <= val <= 113.0):
            return {}, f"Row {row_idx}: Temperature in °F must be 86-113. Received: {val}"
    else:
        if not (min_v <= val <= max_v):
            return {}, f"Row {row_idx}: Out of physiological bounds: {msg}. Received: {val}"

    source = str(row.get("source", "upload")).strip() or "upload"

    return {
        "timestamp": ts,
        "measurement_type": raw_type,
        "value": val,
        "unit": raw_unit,
        "source": source
    }, ""


def process_csv_upload(
    file_bytes: bytes,
    patient_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Parses and ingests a CSV file of measurements for a given patient.
    Checks headers, validates types, bounds, units, and rejects malformed rows.
    Skips duplicates based on (patient_id, measurement_type, timestamp).
    """
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return {"success": False, "error": "CSV file is empty or missing headers."}

    # Normalize header names
    field_map = {f.strip().lower(): f for f in reader.fieldnames if f}
    required = ["timestamp", "measurement_type", "value", "unit"]
    missing = [req for req in required if req not in field_map]
    if missing:
        return {
            "success": False,
            "error": f"CSV missing required columns: {missing}. Found: {list(reader.fieldnames)}"
        }

    # Query latest existing measurement timestamp to detect late arrivals
    latest_existing = db.query(Measurement.timestamp).filter(
        Measurement.patient_id == patient_id
    ).order_by(Measurement.timestamp.desc()).first()
    latest_ts = latest_existing[0].replace(tzinfo=timezone.utc) if latest_existing else None

    # Load existing (type, timestamp) sets to prevent duplicates
    existing_records = set(
        db.query(Measurement.measurement_type, Measurement.timestamp).filter(
            Measurement.patient_id == patient_id
        ).all()
    )
    # Ensure UTC timezone comparability
    existing_keys = {(t, ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts) for t, ts in existing_records}

    valid_objects: List[Measurement] = []
    errors: List[str] = []
    duplicates_skipped = 0
    new_keys_in_batch = set()

    for idx, row in enumerate(reader, start=2):  # line 2 is first data row
        clean_row = {k.strip().lower(): v for k, v in row.items() if k}
        val_data, err = validate_measurement_row(clean_row, idx)
        if err:
            errors.append(err)
            continue

        ts = val_data["timestamp"]
        m_type = val_data["measurement_type"]
        key = (m_type, ts)

        if key in existing_keys or key in new_keys_in_batch:
            duplicates_skipped += 1
            continue

        new_keys_in_batch.add(key)
        is_late = bool(latest_ts and ts < latest_ts)

        valid_objects.append(Measurement(
            patient_id=patient_id,
            timestamp=ts,
            measurement_type=m_type,
            value=val_data["value"],
            unit=val_data["unit"],
            source=val_data["source"],
            is_late_arrival=is_late
        ))

    if valid_objects:
        db.add_all(valid_objects)
        db.commit()

    return {
        "success": True,
        "total_processed": len(valid_objects) + len(errors) + duplicates_skipped,
        "valid_inserted": len(valid_objects),
        "duplicates_skipped": duplicates_skipped,
        "errors": errors
    }


def process_json_upload(
    payload: Dict[str, Any],
    patient_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Parses and ingests a JSON payload containing patient measurements.
    Accepts either { "measurements": [...] } or a direct list of measurement objects.
    """
    if isinstance(payload, list):
        raw_list = payload
    elif isinstance(payload, dict) and "measurements" in payload:
        raw_list = payload["measurements"]
    else:
        return {"success": False, "error": "JSON payload must contain a 'measurements' array or be a list of records."}

    latest_existing = db.query(Measurement.timestamp).filter(
        Measurement.patient_id == patient_id
    ).order_by(Measurement.timestamp.desc()).first()
    latest_ts = latest_existing[0].replace(tzinfo=timezone.utc) if latest_existing else None

    existing_records = set(
        db.query(Measurement.measurement_type, Measurement.timestamp).filter(
            Measurement.patient_id == patient_id
        ).all()
    )
    existing_keys = {(t, ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts) for t, ts in existing_records}

    valid_objects: List[Measurement] = []
    errors: List[str] = []
    duplicates_skipped = 0
    new_keys_in_batch = set()

    for idx, row in enumerate(raw_list, start=1):
        if not isinstance(row, dict):
            errors.append(f"Item {idx}: Expected JSON object, got {type(row).__name__}")
            continue

        val_data, err = validate_measurement_row(row, idx)
        if err:
            errors.append(err)
            continue

        ts = val_data["timestamp"]
        m_type = val_data["measurement_type"]
        key = (m_type, ts)

        if key in existing_keys or key in new_keys_in_batch:
            duplicates_skipped += 1
            continue

        new_keys_in_batch.add(key)
        is_late = bool(latest_ts and ts < latest_ts)

        valid_objects.append(Measurement(
            patient_id=patient_id,
            timestamp=ts,
            measurement_type=m_type,
            value=val_data["value"],
            unit=val_data["unit"],
            source=val_data.get("source", "json_upload"),
            is_late_arrival=is_late
        ))

    if valid_objects:
        db.add_all(valid_objects)
        db.commit()

    return {
        "success": True,
        "total_processed": len(valid_objects) + len(errors) + duplicates_skipped,
        "valid_inserted": len(valid_objects),
        "duplicates_skipped": duplicates_skipped,
        "errors": errors
    }


def process_pdf_report(
    pdf_bytes: bytes,
    patient_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Extracts text from a clinical telemetry PDF report and finds heart rate measurements.
    Regex patterns detect timestamped vitals entries, e.g.:
    '2026-10-23 14:30:00 HR: 74 bpm' or 'Timestamp: 2026-10-23T14:30:00Z Heart Rate: 74 bpm'
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or "\n"
    except Exception as e:
        return {"success": False, "error": f"Failed to parse PDF document: {str(e)}"}

    # Pattern for timestamp and Heart Rate
    # E.g. "2026-10-23 12:00:00 ... HR: 76 bpm" or "2026-10-23T12:00:00 ... Heart Rate: 76.5 bpm"
    pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)'
        r'[\s\S]{0,50}?(?:HR|Heart Rate)[\s:]+(\d{2,3}(?:\.\d+)?)\s*(?:bpm|BPM)?',
        re.IGNORECASE
    )

    matches = pattern.findall(full_text)
    if not matches:
        return {
            "success": False,
            "error": "No timestamped heart rate observations matching standard telemetry formats were found in the PDF text."
        }

    measurements_list = []
    for ts_str, val_str in matches:
        measurements_list.append({
            "timestamp": ts_str,
            "measurement_type": "heart_rate",
            "value": float(val_str),
            "unit": "bpm",
            "source": "pdf_report_extraction"
        })

    return process_json_upload({"measurements": measurements_list}, patient_id, db)

