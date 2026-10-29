import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def get_canonical_db_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Canonical project root: connection.py is at <project_root>/backend/app/database/connection.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))

    root_db = os.path.join(project_root, "patient_twin.db")
    if os.path.exists(root_db):
        db_path = root_db
    else:
        # Fallback to local ./patient_twin.db if root db doesn't exist yet
        db_path = os.path.abspath("patient_twin.db")

    norm_path = db_path.replace("\\", "/")
    return f"sqlite:///{norm_path}"


DATABASE_URL = get_canonical_db_url()

# SQLite needs check_same_thread=False for FastAPI multithreaded requests
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
