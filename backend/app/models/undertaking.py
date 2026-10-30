import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class UndertakingStatus(str, enum.Enum):
    PENDING = "PENDING"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    COMPLIANT = "COMPLIANT"
    DEFICIENT = "DEFICIENT"
    OVERDUE = "OVERDUE"


class TimeBoundUndertaking(Base):
    __tablename__ = "time_bound_undertakings"

    id = Column(Integer, primary_key=True, index=True)
    undertaking_no = Column(String(64), unique=True, index=True, nullable=False)
    
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id"), nullable=True, index=True)
    
    condition_title = Column(String(255), nullable=False)
    condition_description = Column(Text, nullable=False)
    aph_clause = Column(String(100), default="APH 2024-27 Clause 7.12", nullable=False)
    
    statutory_deadline_months = Column(Integer, default=6, nullable=False)
    due_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(32), default=UndertakingStatus.PENDING.value, nullable=False, index=True)
    
    # Institution Evidence Submission
    evidence_submission_date = Column(DateTime, nullable=True)
    evidence_description = Column(Text, nullable=True)
    evidence_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    # AICTE Officer Compliance Review
    officer_review_notes = Column(Text, nullable=True)
    reviewed_by_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", backref="undertakings")
    institution = relationship("Institution", backref="undertakings")
    obligation = relationship("Obligation", backref="undertaking")
    evidence_document = relationship("Document", foreign_keys=[evidence_document_id])
    reviewed_by_officer = relationship("User", foreign_keys=[reviewed_by_officer_id])
