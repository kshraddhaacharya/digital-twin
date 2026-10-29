from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    report_date = Column(String(32), nullable=False)
    file_name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(32), nullable=False)  # 'pdf', 'png', 'jpg', 'jpeg'
    file_size_bytes = Column(Integer, nullable=False, default=0)
    file_hash_sha256 = Column(String(64), nullable=True)
    report_category = Column(String(64), nullable=True, default="uncertain")
    classification_confidence = Column(String(32), nullable=True, default="low")
    classification_evidence = Column(Text, nullable=True)  # JSON-encoded list of matched evidence
    processing_status = Column(String(32), nullable=False, default="Uploaded")  # 'Uploaded', 'Text extracted', 'Clinically structured', 'Partially processed', 'Needs review', 'Failed'
    description = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    clinical_summary = Column(Text, nullable=True)
    structured_findings = Column(Text, nullable=True)  # JSON-encoded structured extraction
    processing_warnings = Column(Text, nullable=True)  # JSON-encoded array of warnings/missing fields
    extracted_vitals = Column(Text, nullable=True)  # JSON-encoded array of vitals for digital twin sync
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="reports")

