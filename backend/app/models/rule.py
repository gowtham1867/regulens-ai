import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class RuleCategory(str, enum.Enum):
    COMPLETENESS = "COMPLETENESS"
    VALIDITY = "VALIDITY"
    CROSS_DOCUMENT = "CROSS_DOCUMENT"
    COMPLIANCE = "COMPLIANCE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    ANOMALY = "ANOMALY"


class RuleSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class EvaluationMethod(str, enum.Enum):
    REQUIRED_DOCUMENT = "REQUIRED_DOCUMENT"
    VALIDITY_DATE_CHECK = "VALIDITY_DATE_CHECK"
    CROSS_DOCUMENT_MATCH = "CROSS_DOCUMENT_MATCH"
    THRESHOLD_EVALUATION = "THRESHOLD_EVALUATION"
    ISSUER_VERIFICATION = "ISSUER_VERIFICATION"
    DUPLICATE_DETECTION = "DUPLICATE_DETECTION"


class RegulatoryRule(Base):
    __tablename__ = "regulatory_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(RuleCategory), nullable=False)
    severity = Column(Enum(RuleSeverity), default=RuleSeverity.MAJOR, nullable=False)
    evaluation_method = Column(Enum(EvaluationMethod), nullable=False)
    
    # Clearly identify illustrative demonstration rules as required by guidelines
    is_illustrative = Column(Boolean, default=True)
    official_source_ref = Column(String(255), default="AICTE Approval Process Handbook (APH)")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    versions = relationship("RegulatoryRuleVersion", back_populates="rule", cascade="all, delete-orphan", order_by="RegulatoryRuleVersion.version_number.desc()")
    findings = relationship("ValidationFinding", back_populates="rule")


class RegulatoryRuleVersion(Base):
    __tablename__ = "regulatory_rule_versions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("regulatory_rules.id"), nullable=False)
    version_number = Column(Integer, default=1, nullable=False)
    requirement_definition = Column(Text, nullable=False)  # JSON or parameter specification
    change_summary = Column(String(255), nullable=True)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rule = relationship("RegulatoryRule", back_populates="versions")


class ApplicationChecklist(Base):
    __tablename__ = "application_checklists"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), index=True, nullable=False)
    academic_year = Column(String(20), default="2025-2026", nullable=False)
    title = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requirements = relationship("ChecklistRequirement", back_populates="checklist", cascade="all, delete-orphan")


class ChecklistRequirement(Base):
    __tablename__ = "checklist_requirements"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("application_checklists.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("regulatory_rules.id"), nullable=True)
    
    document_type = Column(String(100), index=True, nullable=True)
    requirement_title = Column(String(255), nullable=True)
    requirement_description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True)
    applicability_conditions = Column(Text, nullable=True)  # JSON or expression, e.g. "ALL"
    accepted_formats = Column(String(255), default="PDF, JPG, PNG")
    required_fields = Column(Text, nullable=True)  # JSON array of field keys e.g. ["certificate_number", "issue_date"]
    validation_criteria = Column(Text, nullable=True)
    source_clause = Column(String(255), default="AICTE Approval Process Handbook (APH 2024-27)")
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)

    checklist = relationship("ApplicationChecklist", back_populates="requirements")
    rule = relationship("RegulatoryRule")

