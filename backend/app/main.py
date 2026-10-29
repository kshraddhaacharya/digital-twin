import sys
import os

# Ensure both project root and backend dir are in sys.path so imports resolve cleanly,
# whether launched as `uvicorn backend.app.main:app` from root or `uvicorn app.main:app` from backend/
_cur = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_cur, "..", ".."))
_backend_dir = os.path.abspath(os.path.join(_cur, ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database.connection import engine, Base, SessionLocal
from app.database.migration import run_migrations
from app.models import *  # noqa: F401, F403
from app.api import api_router
from app.data.synthetic import generate_synthetic_patient_data
from app.models.patient import Patient
from app.models.measurement import Measurement
from app.digital_twin.engine import DigitalTwinEngine
from app.services.ingestion import parse_iso_datetime


def seed_default_demo_patient():
    """Seeds a default demo patient upon initial database startup if none exist."""
    db = SessionLocal()
    try:
        count = db.query(Patient).count()
        if count == 0:
            print("[INFO] No patients found in database. Seeding demo patient PT-DEMO-001...")
            bundle = generate_synthetic_patient_data(
                patient_id="PT-DEMO-001",
                name="Alice M. Taylor",
                age=56,
                gender="Female",
                baseline_hr=72.0,
                duration_hours=24,
                interval_minutes=15,
                noise_level=1.2,
                include_exercise=True
            )
            pt_data = bundle["patient"]
            patient = Patient(
                id=pt_data["id"],
                name=pt_data["name"],
                age=pt_data["age"],
                gender=pt_data["gender"],
                baseline_heart_rate=pt_data["baseline_heart_rate"],
                height_cm=165.0,
                weight_kg=68.0,
                profile_version=1,
                medical_notes=pt_data["medical_notes"],
                is_synthetic=True
            )
            db.add(patient)
            db.flush()

            meas_objs = []
            for m in bundle["measurements"]:
                meas_objs.append(Measurement(
                    patient_id=pt_data["id"],
                    timestamp=parse_iso_datetime(m["timestamp"]),
                    measurement_type=m["measurement_type"],
                    value=m["value"],
                    unit=m["unit"],
                    source=m["source"],
                    context="resting" if m.get("value", 72) < 95 else "active",
                    data_quality="valid",
                    is_late_arrival=False
                ))
            db.add_all(meas_objs)
            db.commit()

            # Initialize twin at version 1
            DigitalTwinEngine.initialize_twin("PT-DEMO-001", db)
            print("[INFO] Seeded demo patient PT-DEMO-001 with Digital Twin State Version 1.")
    except Exception as e:
        print(f"[WARN] Auto-seeding skipped or encountered error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run safe database schema migrations
    run_migrations()
    # Initialize all database tables
    Base.metadata.create_all(bind=engine)
    seed_default_demo_patient()
    yield


app = FastAPI(
    title="Sovereign Health Twin API",
    description=(
        "Core Digital Twin Engine for continuous patient physiological state modeling, "
        "short-term autoregressive forecasting, counterfactual scenario simulation, "
        "and Web3 decentralized record integrity verification.\n\n"
        "**EDUCATIONAL & RESEARCH PROTOTYPE ONLY**: Not for medical diagnosis or clinical use."
    ),
    version="1.1.0",
    lifespan=lifespan
)

# Configure CORS narrowly for development and local testing
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Global safe error handler to avoid leaking internal tracebacks
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log internally
    print(f"[ERROR] Internal server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please verify your inputs and try again."}
    )

# Register API routes
app.include_router(api_router)


@app.get("/")
def root():
    return {
        "project": "Sovereign Health Twin",
        "docs_url": "/docs",
        "api_prefix": "/api",
        "health": "/api/health"
    }


