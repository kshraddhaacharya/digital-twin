import sqlite3
import os
import bcrypt

DEMO_BCRYPT_HASH = bcrypt.hashpw(b"DemoPassword123!", bcrypt.gensalt()).decode("utf-8")


def get_canonical_db_path(db_path: str = None) -> str:
    if db_path:
        return db_path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    root_db = os.path.join(project_root, "patient_twin.db")
    if os.path.exists(root_db):
        return root_db
    return os.path.abspath("patient_twin.db")


def run_migrations(db_path: str = None):
    """
    Safely adds missing columns to existing SQLite tables without dropping tables
    or overwriting existing patient records.
    """
    target_path = get_canonical_db_path(db_path)
    if not os.path.exists(target_path):
        return

    con = sqlite3.connect(target_path)
    cur = con.cursor()

    def get_columns(table: str):
        try:
            return [info[1] for info in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        except Exception:
            return []

    # 1. Migrations for patients table
    patient_cols = get_columns("patients")
    if patient_cols:
        if "height_cm" not in patient_cols:
            cur.execute("ALTER TABLE patients ADD COLUMN height_cm REAL")
        if "weight_kg" not in patient_cols:
            cur.execute("ALTER TABLE patients ADD COLUMN weight_kg REAL")
        if "profile_version" not in patient_cols:
            cur.execute("ALTER TABLE patients ADD COLUMN profile_version INTEGER NOT NULL DEFAULT 1")

    # 2. Migrations for measurements table
    measurement_cols = get_columns("measurements")
    if measurement_cols:
        if "context" not in measurement_cols:
            cur.execute("ALTER TABLE measurements ADD COLUMN context VARCHAR(32) NOT NULL DEFAULT 'resting'")
        if "data_quality" not in measurement_cols:
            cur.execute("ALTER TABLE measurements ADD COLUMN data_quality VARCHAR(32) NOT NULL DEFAULT 'valid'")

    # 3. Migrations for twin_states table
    twin_cols = get_columns("twin_states")
    if twin_cols:
        if "measurement_context" not in twin_cols:
            cur.execute("ALTER TABLE twin_states ADD COLUMN measurement_context VARCHAR(32) NOT NULL DEFAULT 'resting'")
        if "model_version" not in twin_cols:
            cur.execute("ALTER TABLE twin_states ADD COLUMN model_version VARCHAR(32) NOT NULL DEFAULT '1.0.0'")
        if "data_quality_status" not in twin_cols:
            cur.execute("ALTER TABLE twin_states ADD COLUMN data_quality_status VARCHAR(64) NOT NULL DEFAULT 'good'")
        if "attestation_status" not in twin_cols:
            cur.execute("ALTER TABLE twin_states ADD COLUMN attestation_status VARCHAR(32) NOT NULL DEFAULT 'PENDING'")
        if "previous_state_hash" not in twin_cols:
            cur.execute("ALTER TABLE twin_states ADD COLUMN previous_state_hash VARCHAR(64)")
        if "latest_forecast_time" not in twin_cols:
            cur.execute("ALTER TABLE twin_states ADD COLUMN latest_forecast_time TIMESTAMP")

    # 4. Migrations for users table
    user_cols = get_columns("users")
    if user_cols:
        if "profile_version" not in user_cols:
            cur.execute("ALTER TABLE users ADD COLUMN profile_version INTEGER NOT NULL DEFAULT 1")
        # Ensure default demo user exists for foreign keys and has valid bcrypt credentials
        demo_user = cur.execute("SELECT id, hashed_password FROM users WHERE id = 'USR-DEMO' OR email = 'demo@patient.org'").fetchone()
        if not demo_user:
            cur.execute("""
                INSERT INTO users (id, email, hashed_password, full_name, is_active, patient_id, profile_version, created_at)
                VALUES ('USR-DEMO', 'demo@patient.org', ?, 'Alice M. Taylor (Demo)', 1, 'PT-DEMO-001', 1, CURRENT_TIMESTAMP)
            """, (DEMO_BCRYPT_HASH,))
        else:
            if demo_user[1] == 'demo_hash' or not (demo_user[1].startswith('$2b$') or demo_user[1].startswith('$2a$') or demo_user[1].startswith('$2y$')):
                cur.execute("""
                    UPDATE users SET hashed_password = ? WHERE id = 'USR-DEMO' OR email = 'demo@patient.org'
                """, (DEMO_BCRYPT_HASH,))
            cur.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE (id = 'USR-DEMO' OR email = 'demo@patient.org') AND created_at IS NULL")

    # 5. Migrations for medical_reports table
    report_cols = get_columns("medical_reports")
    if report_cols:
        if "file_hash_sha256" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN file_hash_sha256 VARCHAR(64)")
        if "report_category" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN report_category VARCHAR(64) DEFAULT 'uncertain'")
        if "classification_confidence" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN classification_confidence VARCHAR(32) DEFAULT 'low'")
        if "classification_evidence" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN classification_evidence TEXT")
        if "processing_status" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN processing_status VARCHAR(32) DEFAULT 'Uploaded'")
        if "clinical_summary" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN clinical_summary TEXT")
        if "structured_findings" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN structured_findings TEXT")
        if "processing_warnings" not in report_cols:
            cur.execute("ALTER TABLE medical_reports ADD COLUMN processing_warnings TEXT")

    con.commit()
    con.close()

if __name__ == "__main__":
    run_migrations("patient_twin.db")
    print("Migrations applied successfully to patient_twin.db")
