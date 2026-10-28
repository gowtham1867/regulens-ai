import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class DuplicateMatchType(str, enum.Enum):
    EXACT_HASH = "EXACT_HASH"
    CERTIFICATE_NUMBER = "CERTIFICATE_NUMBER"
    TEXT_SIMILARITY = "TEXT_SIMILARITY"
    SURVEY_NUMBER = "SURVEY_NUMBER"


class DuplicateStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    LEGITIMATE_REUSE = "LEGITIMATE_REUSE"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    DISMISSED = "DISMISSED"


class DuplicateRecord(Base):
    __tablename__ = "duplicate_records"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    matched_document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    
    match_type = Column(Enum(DuplicateMatchType), nullable=False)
    similarity_score = Column(Float, default=1.0, nullable=False)
    
    matched_identifier = Column(String(255), nullable=True)
    explanation = Column(Text, nullable=False)
    status = Column(Enum(DuplicateStatus), default=DuplicateStatus.DETECTED, nullable=False)
    
    officer_resolution_notes = Column(Text, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", backref="duplicate_records")
    document_version = relationship("DocumentVersion", foreign_keys=[document_version_id])
    matched_document_version = relationship("DocumentVersion", foreign_keys=[matched_document_version_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])

