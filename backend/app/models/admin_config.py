from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from app.database import Base


class HolidayCalendar(Base):
    __tablename__ = "holiday_calendars"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String(64), default="ALL", nullable=False, index=True)  # ALL, SOUTHERN, NORTHERN, WESTERN, EASTERN, or STATE_TN, STATE_DL
    date = Column(DateTime, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    is_statutory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WorkflowRouteTemplate(Base):
    __tablename__ = "workflow_route_templates"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(64), unique=True, nullable=False, index=True)  # ApplicationCategory
    route_type = Column(String(32), nullable=False)  # ONLY_SCRUTINY, SCRUTINY_EVC, etc.
    stages_json = Column(Text, nullable=False)  # JSON array of stage names: ["SCRUTINY_STAGE", "EVC_STAGE", "FINAL_APPROVAL"]
    
    default_scrutiny_days = Column(Integer, default=15, nullable=False)
    default_evc_days = Column(Integer, default=20, nullable=False)
    default_sac_shc_days = Column(Integer, default=10, nullable=False)
    default_institution_clarification_days = Column(Integer, default=7, nullable=False)
    deadline_type = Column(String(32), default="WORKING_DAYS", nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SystemAuditBlock(Base):
    __tablename__ = "system_audit_blocks"

    id = Column(Integer, primary_key=True, index=True)
    block_index = Column(Integer, unique=True, nullable=False, index=True)
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)
    event_count = Column(Integer, default=0, nullable=False)
    payload_summary = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
