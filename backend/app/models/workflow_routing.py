import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class ApplicationRouteType(str, enum.Enum):
    ONLY_SCRUTINY = "ONLY_SCRUTINY"
    SCRUTINY_EVC = "SCRUTINY_EVC"
    EVC_SAC_SHC = "EVC_SAC_SHC"
    ONLY_EVC = "ONLY_EVC"
    FULL_SCRUTINY_EVC_SAC = "FULL_SCRUTINY_EVC_SAC"
    CUSTOM = "CUSTOM"


class WorkflowStage(str, enum.Enum):
    SCRUTINY_STAGE = "SCRUTINY_STAGE"
    RE_SCRUTINY = "RE_SCRUTINY"
    EVC_STAGE = "EVC_STAGE"
    SAC_SHC_STAGE = "SAC_SHC_STAGE"
    FINAL_APPROVAL = "FINAL_APPROVAL"
    CLOSED = "CLOSED"


class ApplicationWorkflowRouting(Base):
    __tablename__ = "application_workflow_routings"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False, index=True)
    
    route_type = Column(String(32), default=ApplicationRouteType.ONLY_SCRUTINY.value, nullable=False)
    current_stage = Column(String(32), default=WorkflowStage.SCRUTINY_STAGE.value, nullable=False)
    stage_entry_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    stage_deadline = Column(DateTime, nullable=True)
    
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_committee = Column(String(128), default="Scrutiny Committee (Region)", nullable=True)
    
    processing_status = Column(String(32), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS, AWAITING_CLARIFICATION, STAGE_COMPLETED, REVERTED, REJECTED, APPROVED
    is_completed = Column(Boolean, default=False, nullable=False)
    next_eligible_stage = Column(String(32), nullable=True)
    
    routing_reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", backref="workflow_routing", uselist=False)
    assigned_officer = relationship("User")
    stage_history = relationship("StageMovementHistory", back_populates="routing", cascade="all, delete-orphan", order_by="StageMovementHistory.id.asc()")


class StageMovementHistory(Base):
    __tablename__ = "stage_movement_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    routing_id = Column(Integer, ForeignKey("application_workflow_routings.id"), nullable=True)
    
    from_stage = Column(String(32), nullable=True)
    to_stage = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)  # ADVANCE, RETURN_FOR_CLARIFICATION, REVERT, RE_SCRUTINY, ESCALATE, APPROVE, REJECT
    reason = Column(Text, nullable=False)  # Mandatory recorded reason
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", backref="stage_history")
    routing = relationship("ApplicationWorkflowRouting", back_populates="stage_history")
    officer = relationship("User")
