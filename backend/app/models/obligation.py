import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base


class ObligationType(str, enum.Enum):
    APPLICATION_SCRUTINY = "APPLICATION_SCRUTINY"
    RE_SCRUTINY = "RE_SCRUTINY"
    EVC_SCHEDULING = "EVC_SCHEDULING"
    EVC_COMPLETION = "EVC_COMPLETION"
    SAC_SHC_REVIEW = "SAC_SHC_REVIEW"
    INSTITUTION_CLARIFICATION = "INSTITUTION_CLARIFICATION"
    DOCUMENT_SUBMISSION = "DOCUMENT_SUBMISSION"
    LEASE_RENEWAL = "LEASE_RENEWAL"
    FIRE_NOC_RENEWAL = "FIRE_NOC_RENEWAL"
    AFFILIATION_RENEWAL = "AFFILIATION_RENEWAL"
    TIME_BOUND_UNDERTAKING = "TIME_BOUND_UNDERTAKING"
    COMPLIANCE_VERIFICATION = "COMPLIANCE_VERIFICATION"
    OTHER = "OTHER"


class ObligationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    MET = "MET"
    OVERDUE = "OVERDUE"
    BREACHED = "BREACHED"
    WAIVED = "WAIVED"


class ClockState(str, enum.Enum):
    RUNNING = "RUNNING"
    PAUSED_INSTITUTION = "PAUSED_INSTITUTION"
    PAUSED_AICTE = "PAUSED_AICTE"
    PAUSED_LEGAL_HOLD = "PAUSED_LEGAL_HOLD"
    PAUSED_SOURCE = "PAUSED_SOURCE"
    STOPPED_MET = "STOPPED_MET"
    STOPPED_WAIVED = "STOPPED_WAIVED"
    BREACHED = "BREACHED"


class ResponsibleRole(str, enum.Enum):
    INSTITUTION = "INSTITUTION"
    AICTE_OFFICER = "AICTE_OFFICER"
    SCRUTINY_COMMITTEE = "SCRUTINY_COMMITTEE"
    EVC_PANEL = "EVC_PANEL"
    SAC_SHC_COMMITTEE = "SAC_SHC_COMMITTEE"
    REGIONAL_OFFICER = "REGIONAL_OFFICER"
    BUREAU_HEAD = "BUREAU_HEAD"
    ADMIN = "ADMIN"


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True, index=True)
    obligation_no = Column(String(64), unique=True, index=True, nullable=False)
    
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    obligation_type = Column(String(64), default=ObligationType.APPLICATION_SCRUTINY.value, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Responsibility mapping
    responsible_entity = Column(String(255), nullable=False)  # Name of institution or officer post
    responsible_role = Column(String(64), default=ResponsibleRole.AICTE_OFFICER.value, nullable=False)
    responsible_post = Column(String(128), default="Scrutiny Cell", nullable=False)
    
    # Regulatory origin
    source_event = Column(String(128), nullable=False)  # APPLICATION_SUBMISSION, CLARIFICATION_ISSUED, etc.
    source_rule_id = Column(Integer, ForeignKey("regulatory_rules.id"), nullable=True)
    aph_clause = Column(String(100), default="APH 2024-27 Clause 2.3", nullable=False)
    is_aph_verified = Column(Boolean, default=True, nullable=False)  # False = administrator configured
    
    # Timing & Clock Parameters
    deadline_type = Column(String(32), default="WORKING_DAYS", nullable=False)  # WORKING_DAYS, CALENDAR_DAYS
    configured_days = Column(Integer, default=30, nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False, index=True)
    original_due_date = Column(DateTime, nullable=False)
    
    # Current Clock & Status
    status = Column(String(32), default=ObligationStatus.RUNNING.value, nullable=False, index=True)
    clock_state = Column(String(32), default=ClockState.RUNNING.value, nullable=False)
    
    # Clock Adjustment Accumulators
    total_paused_days = Column(Integer, default=0, nullable=False)
    approved_extension_days = Column(Integer, default=0, nullable=False)
    excluded_holidays_count = Column(Integer, default=0, nullable=False)
    
    # Evidence & Verification
    evidence_refs = Column(Text, nullable=True)  # JSON list of document IDs or URLs
    completion_date = Column(DateTime, nullable=True)
    verification_status = Column(String(32), default="UNVERIFIED", nullable=False)  # UNVERIFIED, PENDING_VERIFICATION, VERIFIED, REJECTED
    escalation_level = Column(Integer, default=0, nullable=False)  # 0=Normal, 1=7d Warning, 2=3d Urgent, 3=Overdue Escalation
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    institution = relationship("Institution", backref="obligations")
    application = relationship("Application", backref="obligations")
    source_rule = relationship("RegulatoryRule")
    event_history = relationship("ObligationEventHistory", back_populates="obligation", cascade="all, delete-orphan", order_by="ObligationEventHistory.id.asc()")
    clock_intervals = relationship("ClockInterval", back_populates="obligation", cascade="all, delete-orphan", order_by="ClockInterval.id.asc()")


class ObligationEventHistory(Base):
    __tablename__ = "obligation_event_history"

    id = Column(Integer, primary_key=True, index=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)  # CREATED, CLOCK_PAUSED, CLOCK_RESUMED, EXTENSION_APPROVED, COMPLETED, ESCALATED, REMINDER
    triggered_by = Column(String(128), default="SYSTEM", nullable=False)
    reason = Column(Text, nullable=False)
    previous_state = Column(String(64), nullable=True)
    new_state = Column(String(64), nullable=False)
    clock_interval_days = Column(Integer, nullable=True)
    audit_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    obligation = relationship("Obligation", back_populates="event_history")


class ClockInterval(Base):
    __tablename__ = "clock_intervals"

    id = Column(Integer, primary_key=True, index=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id"), nullable=False, index=True)
    clock_state = Column(String(32), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    reason = Column(String(255), nullable=True)
    actor = Column(String(128), default="SYSTEM", nullable=False)

    obligation = relationship("Obligation", back_populates="clock_intervals")
