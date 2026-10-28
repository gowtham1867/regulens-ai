import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base


class DocumentType(str, enum.Enum):
    LAND_DOCUMENT = "LAND_DOCUMENT"
    LAND_DOCUMENTS = "LAND_DOCUMENTS"
    LAND_USE_CERTIFICATE = "LAND_USE_CERTIFICATE"
    FIRE_SAFETY_CERTIFICATE = "FIRE_SAFETY_CERTIFICATE"
    BUILDING_PLAN = "BUILDING_PLAN"
    OCCUPANCY_CERTIFICATE = "OCCUPANCY_CERTIFICATE"
    AFFILIATION_CERTIFICATE = "AFFILIATION_CERTIFICATE"
    AFFILIATION_ORDER = "AFFILIATION_ORDER"
    FACULTY_LIST = "FACULTY_LIST"
    INFRASTRUCTURE_EVIDENCE = "INFRASTRUCTURE_EVIDENCE"
    AUDIT_STATEMENT = "AUDIT_STATEMENT"
    AUDITED_FINANCIALS = "AUDITED_FINANCIALS"
    OTHER = "OTHER"


class ProcessingStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRY_AVAILABLE = "RETRY_AVAILABLE"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    title = Column(String(255), nullable=False)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, default=1, nullable=False)
    
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)  # SHA-256
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, default=1)
    
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.QUEUED, nullable=False)
    error_message = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    raw_extracted_text = Column(Text, nullable=True)
    
    # Correction tracking
    correction_submission_id = Column(Integer, ForeignKey("correction_submissions.id"), nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="versions")
    extracted_fields = relationship("ExtractedField", back_populates="document_version", cascade="all, delete-orphan")
    verification_attempts = relationship("VerificationAttempt", back_populates="document_version", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    
    field_key = Column(String(100), index=True, nullable=False)
    field_label = Column(String(200), nullable=False)
    extracted_value = Column(Text, nullable=False)
    normalized_value = Column(String(255), nullable=True)
    source_page = Column(Integer, default=1)
    confidence = Column(Float, default=1.0)
    extraction_method = Column(String(100), default="OCR_AND_PATTERN")  # TEXT_EXTRACTION, OCR, REGEX_PATTERN
    
    # Authorized manual correction
    is_manually_corrected = Column(Boolean, default=False)
    corrected_value = Column(Text, nullable=True)
    corrected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    correction_reason = Column(String(255), nullable=True)
    corrected_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    document_version = relationship("DocumentVersion", back_populates="extracted_fields")

