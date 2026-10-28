import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class DeficiencyType(str, enum.Enum):
    MISSING_MANDATORY_DOCUMENT = "MISSING_MANDATORY_DOCUMENT"
    MISSING_DOCUMENT = "MISSING_MANDATORY_DOCUMENT"
    MISSING_CONDITIONAL_DOCUMENT = "MISSING_CONDITIONAL_DOCUMENT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    DOCUMENT_TYPE_MISMATCH = "DOCUMENT_TYPE_MISMATCH"
    EXPIRED_DOCUMENT = "EXPIRED_DOCUMENT"
    EXPIRED_CERTIFICATE = "EXPIRED_DOCUMENT"
    DUPLICATE_FILE = "DUPLICATE_FILE"
    POTENTIAL_DUPLICATE_DOCUMENT = "POTENTIAL_DUPLICATE_DOCUMENT"
    CONFLICTING_INFORMATION = "CONFLICTING_INFORMATION"
    SUSPICIOUS_INTEGRITY = "SUSPICIOUS_INTEGRITY"
    ISSUER_MISMATCH = "ISSUER_MISMATCH"
    UNREADABLE_CONTENT = "UNREADABLE_CONTENT"


class DeficiencyStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"
    SUPERSEDED = "SUPERSEDED"


class ApplicationDeficiency(Base):
    __tablename__ = "application_deficiencies"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    rule_code = Column(String(100), index=True, nullable=False)
    document_type = Column(String(100), nullable=True)
    
    deficiency_type = Column(Enum(DeficiencyType), nullable=False)
    severity = Column(String(50), default="CRITICAL", nullable=False)  # CRITICAL, MAJOR, MINOR, INFO
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    supporting_evidence = Column(Text, nullable=True)
    required_action = Column(Text, nullable=False)
    
    responsible_party = Column(String(100), default="INSTITUTION", nullable=False)
    status = Column(Enum(DeficiencyStatus), default=DeficiencyStatus.OPEN, nullable=False)
    
    # Traceability to specific version / resolution
    affected_document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    resolved_by_document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    application = relationship("Application", backref="deficiencies")
    affected_document_version = relationship("DocumentVersion", foreign_keys=[affected_document_version_id])
    resolved_by_document_version = relationship("DocumentVersion", foreign_keys=[resolved_by_document_version_id])

