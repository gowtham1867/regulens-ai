import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class FindingStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    NOT_EVALUATED = "NOT_EVALUATED"
    RESOLVED = "RESOLVED"
    SUPERSEDED = "SUPERSEDED"


class TriggerType(str, enum.Enum):
    INITIAL_VALIDATION = "INITIAL_VALIDATION"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"
    CHANGE_AWARE_REVALIDATION = "CHANGE_AWARE_REVALIDATION"


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    run_number = Column(Integer, default=1, nullable=False)
    trigger_type = Column(Enum(TriggerType), default=TriggerType.INITIAL_VALIDATION, nullable=False)
    triggering_change = Column(String(255), nullable=True)
    
    total_rules_evaluated = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    manual_review_count = Column(Integer, default=0)
    
    # Change-aware revalidation metrics
    reused_checks_count = Column(Integer, default=0)
    reexecuted_checks_count = Column(Integer, default=0)
    superseded_findings_count = Column(Integer, default=0)
    
    executed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="validation_runs")
    findings = relationship("ValidationFinding", back_populates="validation_run", cascade="all, delete-orphan")


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id = Column(Integer, primary_key=True, index=True)
    validation_run_id = Column(Integer, ForeignKey("validation_runs.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("regulatory_rules.id"), nullable=False)
    
    status = Column(Enum(FindingStatus), nullable=False)
    severity = Column(String(50), default="MAJOR", nullable=False)
    
    affected_claim_field = Column(String(100), nullable=True)
    affected_document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    
    expected_value = Column(String(255), nullable=True)
    observed_value = Column(String(255), nullable=True)
    explanation = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    
    # State tracking: Historical preservation vs current state
    is_active = Column(Boolean, default=True)
    superseded_by_finding_id = Column(Integer, ForeignKey("validation_findings.id"), nullable=True)
    is_resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    validation_run = relationship("ValidationRun", back_populates="findings")
    application = relationship("Application", back_populates="findings")
    rule = relationship("RegulatoryRule", back_populates="findings")
    affected_document_version = relationship("DocumentVersion")
    evidence_links = relationship("FindingEvidenceLink", back_populates="finding", cascade="all, delete-orphan")


class FindingEvidenceLink(Base):
    __tablename__ = "finding_evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("validation_findings.id"), nullable=False)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    extracted_field_id = Column(Integer, ForeignKey("extracted_fields.id"), nullable=True)
    source_page = Column(Integer, default=1)
    evidence_excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("ValidationFinding", back_populates="evidence_links")
    document_version = relationship("DocumentVersion")
    extracted_field = relationship("ExtractedField")

