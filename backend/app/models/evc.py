import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class EVCStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PANEL_PROPOSED = "PANEL_PROPOSED"
    SCHEDULED = "SCHEDULED"
    VISITED = "VISITED"
    REPORT_PENDING = "REPORT_PENDING"
    REPORT_RECEIVED = "REPORT_RECEIVED"
    CLOSED = "CLOSED"
    DELAYED = "DELAYED"


class EVCSchedule(Base):
    __tablename__ = "evc_schedules"

    id = Column(Integer, primary_key=True, index=True)
    evc_no = Column(String(64), unique=True, index=True, nullable=False)
    
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    region = Column(String(64), default="Southern Regional Office", nullable=False)
    
    status = Column(String(32), default=EVCStatus.QUEUED.value, nullable=False, index=True)
    scheduled_date = Column(DateTime, nullable=True)
    visit_location = Column(String(255), nullable=True)
    
    # Expert Panel Data (JSON-serialized arrays of expert objects)
    proposed_panel = Column(Text, nullable=True)
    approved_panel = Column(Text, nullable=True)
    
    # Conflict-of-interest verification
    conflict_check_passed = Column(Boolean, default=True, nullable=False)
    conflict_check_notes = Column(Text, nullable=True)
    
    # Statutory officer oversight
    approved_by_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    officer_approval_date = Column(DateTime, nullable=True)
    
    # Inspection Report
    report_submission_date = Column(DateTime, nullable=True)
    report_recommendation = Column(String(64), nullable=True)  # RECOMMENDED, DEFICIENT, REJECTED
    report_summary = Column(Text, nullable=True)
    report_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", backref="evc_schedules")
    institution = relationship("Institution", backref="evc_schedules")
    approved_by_officer = relationship("User", foreign_keys=[approved_by_officer_id])
    report_document = relationship("Document", foreign_keys=[report_document_id])


class EVCExpert(Base):
    __tablename__ = "evc_experts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    designation = Column(String(128), nullable=False)
    institution = Column(String(255), nullable=False)
    specialization = Column(String(128), nullable=False)
    region = Column(String(64), nullable=False)
    state = Column(String(64), nullable=False)
    active_visits_count = Column(Integer, default=0, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
