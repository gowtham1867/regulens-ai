import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
    CORRECTION_SUBMITTED = "CORRECTION_SUBMITTED"
    REVALIDATION = "REVALIDATION"
    READY_FOR_DECISION = "READY_FOR_DECISION"
    APPROVED = "APPROVED"
    RETURNED = "RETURNED"
    REJECTED = "REJECTED"


class ApplicationCategory(str, enum.Enum):
    EXTENSION_OF_APPROVAL = "EXTENSION_OF_APPROVAL"
    NEW_INSTITUTION = "NEW_INSTITUTION"
    INCREASE_IN_INTAKE = "INCREASE_IN_INTAKE"
    INTRODUCTION_OF_NEW_COURSE = "INTRODUCTION_OF_NEW_COURSE"
    CHANGE_OF_SITE = "CHANGE_OF_SITE"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(100), unique=True, index=True, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    submitting_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    category = Column(Enum(ApplicationCategory), default=ApplicationCategory.EXTENSION_OF_APPROVAL, nullable=False)
    academic_year = Column(String(20), default="2025-2026", nullable=False)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT, nullable=False)
    
    # Declared claims
    declared_intake = Column(Integer, nullable=True)
    declared_land_acres = Column(Float, nullable=True)
    declared_built_up_sqm = Column(Float, nullable=True)
    declared_faculty_count = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Distinguish demonstration seed records from real records (Rule 2)
    is_demo_seed = Column(Boolean, default=False)
    
    submission_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="applications")
    submitting_user = relationship("User", foreign_keys=[submitting_user_id])
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    claims = relationship("ApplicationClaim", back_populates="application", cascade="all, delete-orphan")
    status_history = relationship("ApplicationStatusHistory", back_populates="application", cascade="all, delete-orphan")
    validation_runs = relationship("ValidationRun", back_populates="application", cascade="all, delete-orphan")
    findings = relationship("ValidationFinding", back_populates="application", cascade="all, delete-orphan")
    clarifications = relationship("ClarificationRequest", back_populates="application", cascade="all, delete-orphan")
    reviews = relationship("OfficerReview", back_populates="application", cascade="all, delete-orphan")
    decisions = relationship("WorkflowDecision", back_populates="application", cascade="all, delete-orphan")


class ApplicationClaim(Base):
    __tablename__ = "application_claims"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    claim_type = Column(String(100), nullable=False)  # LAND_AREA, FIRE_SAFETY_EXPIRY, APPROVED_INTAKE, AFFILIATION_STATUS
    field_name = Column(String(100), nullable=False)
    declared_value = Column(String(255), nullable=False)
    source_reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="claims")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="status_history")

