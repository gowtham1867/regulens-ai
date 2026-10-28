import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class ClarificationStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"


class DecisionType(str, enum.Enum):
    APPROVE = "APPROVE"
    RETURN = "RETURN"
    REJECT = "REJECT"
    REQUEST_CORRECTION = "REQUEST_CORRECTION"
    REQUEST_DOCUMENTS = "REQUEST_DOCUMENTS"
    UNDER_REVIEW = "UNDER_REVIEW"


class ClarificationRequest(Base):
    __tablename__ = "clarification_requests"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    requesting_officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    subject = Column(String(255), nullable=False)
    requested_information = Column(Text, nullable=False)
    instructions_for_correction = Column(Text, nullable=False)
    
    relevant_finding_id = Column(Integer, ForeignKey("validation_findings.id"), nullable=True)
    relevant_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    status = Column(Enum(ClarificationStatus), default=ClarificationStatus.OPEN, nullable=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="clarifications")
    requesting_officer = relationship("User")
    relevant_finding = relationship("ValidationFinding")
    relevant_document = relationship("Document")
    correction_submissions = relationship("CorrectionSubmission", back_populates="clarification_request", cascade="all, delete-orphan")


class CorrectionSubmission(Base):
    __tablename__ = "correction_submissions"

    id = Column(Integer, primary_key=True, index=True)
    clarification_request_id = Column(Integer, ForeignKey("clarification_requests.id"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    submitting_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clarification_request = relationship("ClarificationRequest", back_populates="correction_submissions")
    application = relationship("Application")
    submitting_user = relationship("User")


class OfficerReview(Base):
    __tablename__ = "officer_reviews"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    review_stage = Column(String(100), default="SCRUTINY_REVIEW")
    review_notes = Column(Text, nullable=False)
    recommended_action = Column(String(50), nullable=True)  # APPROVE, RETURN, REJECT, REQUEST_CLARIFICATION
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="reviews")
    officer = relationship("User", back_populates="reviewed_applications")


class WorkflowDecision(Base):
    __tablename__ = "workflow_decisions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    decision = Column(Enum(DecisionType), nullable=False)
    justification = Column(Text, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    
    # Override tracking per security requirements
    is_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    
    decided_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="decisions")
    officer = relationship("User", back_populates="decisions")

