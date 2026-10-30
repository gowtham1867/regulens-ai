from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.database import Base


class SchedulerJob(Base):
    __tablename__ = "scheduler_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(64), unique=True, nullable=False, index=True)
    job_type = Column(String(64), nullable=False)  # DEADLINE_MONITOR, CLOCK_EVALUATOR, ESCALATION_DISPATCHER, EXPIRY_SCANNER
    
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    status = Column(String(32), default="IDLE", nullable=False)  # IDLE, RUNNING, SUCCESS, FAILED
    last_result = Column(Text, nullable=True)
    
    interval_seconds = Column(Integer, default=60, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
