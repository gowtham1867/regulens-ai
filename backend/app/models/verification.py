import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class VerificationOutcome(str, enum.Enum):
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    NOT_EVALUATED = "NOT_EVALUATED"


class VerificationMethod(str, enum.Enum):
    API_LOOKUP = "API_LOOKUP"
    QR_CODE = "QR_CODE"
    DIGITAL_SIGNATURE = "DIGITAL_SIGNATURE"
    REPOSITORY_LOOKUP = "REPOSITORY_LOOKUP"
    MANUAL_EVIDENCE = "MANUAL_EVIDENCE"


class VerificationSource(Base):
    __tablename__ = "verification_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    authority_type = Column(String(100), nullable=False)  # FIRE_SERVICE, REVENUE_LAND, UNIVERSITY, MOCK_REGISTRY
    verification_method = Column(Enum(VerificationMethod), default=VerificationMethod.API_LOOKUP, nullable=False)
    
    # Honest disclosure of simulated vs live verification
    is_simulated = Column(Boolean, default=True)
    simulated_badge_label = Column(String(100), default="SIMULATED VERIFICATION — DEMONSTRATION DATA")
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    last_health_check = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    attempts = relationship("VerificationAttempt", back_populates="source")


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    verification_source_id = Column(Integer, ForeignKey("verification_sources.id"), nullable=False)
    
    certificate_number = Column(String(100), nullable=True)
    verification_method = Column(Enum(VerificationMethod), nullable=False)
    outcome = Column(Enum(VerificationOutcome), nullable=False)
    
    # Cache & Change-aware verification reuse (Section 14)
    cache_key = Column(String(128), index=True, nullable=True)
    is_reused = Column(Boolean, default=False)
    reused_from_attempt_id = Column(Integer, ForeignKey("verification_attempts.id"), nullable=True)
    is_invalidated = Column(Boolean, default=False)
    invalidation_reason = Column(String(255), nullable=True)
    
    # Persistent flag for demonstration
    is_simulated = Column(Boolean, default=True)
    
    evidence_payload = Column(Text, nullable=True)  # JSON record returned by source
    failure_reason = Column(Text, nullable=True)
    
    request_timestamp = Column(DateTime, default=datetime.utcnow)
    response_timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document_version = relationship("DocumentVersion", back_populates="verification_attempts")
    source = relationship("VerificationSource", back_populates="attempts")

